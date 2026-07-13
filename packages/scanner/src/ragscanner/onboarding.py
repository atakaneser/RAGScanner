"""Safe, bounded discovery helpers for the interactive CLI onboarding flow."""

import json
import re
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ragscanner.domain.helpers import mask_secret_like_values, normalize_control_characters

SUPPORTED_LOCAL_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".pdf", ".docx"})
COMMON_SOURCE_DIRECTORY_NAMES = (
    "knowledge-base",
    "knowledge_base",
    "knowledge",
    "documents",
    "docs",
    "uploads",
)
OPENWEBUI_LOOPBACK_ENDPOINTS = (
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
)
CONTAINER_RUNTIME_NAMES = ("docker", "podman", "nerdctl", "finch")
MAX_RUNTIME_OUTPUT_BYTES = 1_000_000
MAX_OPENWEBUI_RESPONSE_BYTES = 1_000_000
_OPENWEBUI_HINTS = ("open-webui", "open_webui", "openwebui")
_PUBLISHED_PORT = re.compile(
    r"(?P<host>\[[0-9a-fA-F:]+\]|[0-9a-fA-F:.]+|localhost):"
    r"(?P<host_port>\d+)->(?P<container_port>\d+)/(?:tcp|TCP)"
)


@dataclass(frozen=True, slots=True)
class LocalSourceCandidate:
    """A local path that looks like a supported scan source."""

    path: Path
    supported_file_count: int


@dataclass(frozen=True, slots=True)
class ServiceCandidate:
    """A possible local service discovered without authentication or content access."""

    base_url: str
    health_path: str
    discovery_source: str = "common_loopback"
    runtime: str | None = None
    container_name: str | None = None
    image: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeBaseCandidate:
    """Bounded OpenWebUI knowledge-base metadata visible to the authenticated user."""

    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class OpenWebUIFileCandidate:
    """Accessible OpenWebUI file metadata and its visible knowledge-base memberships."""

    id: str
    filename: str
    status: str | None
    knowledge_base_ids: tuple[str, ...]


class OpenWebUIDiscoveryError(RuntimeError):
    """Safe user-facing OpenWebUI discovery failure."""


def _supported_file_count(path: Path, *, limit: int = 200) -> int:
    """Count only immediate supported files with a strict work bound."""
    count = 0
    try:
        entries = path.iterdir()
        for index, entry in enumerate(entries):
            if index >= limit:
                break
            if entry.is_file() and entry.suffix.casefold() in SUPPORTED_LOCAL_EXTENSIONS:
                count += 1
    except OSError:
        return 0
    return count


def discover_local_sources(root: Path) -> list[LocalSourceCandidate]:
    """Inspect only ``root`` and known immediate children; never crawl the home directory."""
    resolved = root.expanduser().resolve()
    candidates: list[LocalSourceCandidate] = []
    root_count = _supported_file_count(resolved)
    if root_count:
        candidates.append(LocalSourceCandidate(path=resolved, supported_file_count=root_count))
    for name in COMMON_SOURCE_DIRECTORY_NAMES:
        candidate = resolved / name
        if not candidate.is_dir():
            continue
        count = _supported_file_count(candidate)
        if count:
            candidates.append(LocalSourceCandidate(path=candidate, supported_file_count=count))
    return sorted(candidates, key=lambda item: (-item.supported_file_count, str(item.path)))


def _runtime_records(output: str) -> list[dict[str, object]]:
    stripped = output.strip()
    if not stripped or len(stripped.encode("utf-8")) > MAX_RUNTIME_OUTPUT_BYTES:
        return []
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    records: list[dict[str, object]] = []
    for line in stripped.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def _record_text(record: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
    return ""


def _loopback_base_urls(record: dict[str, object]) -> list[str]:
    name = _record_text(record, "Names", "Name", "names", "name")
    image = _record_text(record, "Image", "image")
    ports = _record_text(record, "Ports", "ports")
    identity = f"{name} {image}".casefold()
    hinted = any(hint in identity for hint in _OPENWEBUI_HINTS)
    endpoints: list[str] = []
    for match in _PUBLISHED_PORT.finditer(ports):
        host = match.group("host").strip("[]").casefold()
        host_port = int(match.group("host_port"))
        container_port = int(match.group("container_port"))
        if host not in {"0.0.0.0", "::", "127.0.0.1", "localhost"}:
            continue
        if not hinted and container_port not in {3000, 8080}:
            continue
        endpoints.append(f"http://127.0.0.1:{host_port}")
    return endpoints


def discover_container_openwebui_endpoints(
    *, timeout_seconds: float = 2.0
) -> dict[str, tuple[str, str | None, str | None]]:
    """Read bounded local runtime metadata without a shell and return loopback endpoints."""
    endpoints: dict[str, tuple[str, str | None, str | None]] = {}
    for runtime in CONTAINER_RUNTIME_NAMES:
        executable = shutil.which(runtime)
        if executable is None:
            continue
        try:
            result = subprocess.run(  # noqa: S603
                [executable, "ps", "--format", "{{json .}}"],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        for record in _runtime_records(result.stdout):
            name = _record_text(record, "Names", "Name", "names", "name") or None
            image = _record_text(record, "Image", "image") or None
            for endpoint in _loopback_base_urls(record):
                endpoints.setdefault(endpoint, (runtime, name, image))
    return endpoints


def discover_openwebui_services(
    *,
    endpoints: Iterable[str] | None = None,
    timeout_seconds: float = 0.75,
    include_container_runtimes: bool = False,
) -> list[ServiceCandidate]:
    """Probe bounded loopback health endpoints after explicit caller consent."""
    runtime_endpoints = (
        discover_container_openwebui_endpoints() if include_container_runtimes else {}
    )
    candidates = list(endpoints if endpoints is not None else OPENWEBUI_LOOPBACK_ENDPOINTS)
    candidates.extend(runtime_endpoints)
    discovered: list[ServiceCandidate] = []
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for base_url in dict.fromkeys(candidates):
            health_path = "/health"
            try:
                with client.stream("GET", f"{base_url}{health_path}") as response:
                    if response.status_code == 200:
                        runtime_details = runtime_endpoints.get(base_url)
                        discovered.append(
                            ServiceCandidate(
                                base_url=base_url,
                                health_path=health_path,
                                discovery_source=(
                                    "container_runtime" if runtime_details else "common_loopback"
                                ),
                                runtime=runtime_details[0] if runtime_details else None,
                                container_name=runtime_details[1] if runtime_details else None,
                                image=runtime_details[2] if runtime_details else None,
                            )
                        )
            except httpx.HTTPError:
                continue
    return discovered


def _safe_remote_text(value: object, *, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_control_characters(mask_secret_like_values(value))[:limit]


def _openwebui_headers(base_url: str, api_key: str) -> dict[str, str]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise OpenWebUIDiscoveryError(
            "Only an explicitly discovered loopback service is supported."
        )
    if not api_key.strip():
        raise OpenWebUIDiscoveryError("An OpenWebUI API key is required.")
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _openwebui_page(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    params: dict[str, int | bool],
) -> tuple[list[object], int | None]:
    try:
        response = client.get(url, headers=headers, params=params)
    except httpx.HTTPError as error:
        raise OpenWebUIDiscoveryError("OpenWebUI metadata discovery failed.") from error
    if response.status_code in {401, 403}:
        raise OpenWebUIDiscoveryError("OpenWebUI rejected the API key or its metadata permission.")
    if response.status_code != 200:
        raise OpenWebUIDiscoveryError(
            f"OpenWebUI metadata discovery returned HTTP {response.status_code}."
        )
    if len(response.content) > MAX_OPENWEBUI_RESPONSE_BYTES:
        raise OpenWebUIDiscoveryError("OpenWebUI returned an oversized discovery response.")
    try:
        payload = response.json()
    except ValueError as error:
        raise OpenWebUIDiscoveryError("OpenWebUI returned malformed discovery data.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise OpenWebUIDiscoveryError("OpenWebUI returned an unsupported discovery schema.")
    total = payload.get("total")
    return payload["items"], total if isinstance(total, int) else None


def discover_openwebui_knowledge_bases(
    base_url: str,
    api_key: str,
    *,
    max_pages: int = 10,
    max_items: int = 300,
    timeout_seconds: float = 3.0,
) -> list[KnowledgeBaseCandidate]:
    """List bounded knowledge-base metadata; never retain or return the supplied credential."""
    headers = _openwebui_headers(base_url, api_key)
    discovered: list[KnowledgeBaseCandidate] = []
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds), follow_redirects=False, trust_env=False
    ) as client:
        for page in range(1, max_pages + 1):
            items, total = _openwebui_page(
                client,
                f"{base_url.rstrip('/')}/api/v1/knowledge/",
                headers,
                {"page": page},
            )
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = _safe_remote_text(item.get("id"), limit=160)
                name = _safe_remote_text(item.get("name"), limit=240)
                if not item_id or not name:
                    continue
                discovered.append(
                    KnowledgeBaseCandidate(
                        id=item_id,
                        name=name,
                        description=_safe_remote_text(item.get("description"), limit=500),
                    )
                )
                if len(discovered) >= max_items:
                    return discovered
            if not items or (total is not None and len(discovered) >= total):
                break
    return discovered


def discover_openwebui_files(
    base_url: str,
    api_key: str,
    *,
    max_pages: int = 10,
    max_items: int = 500,
    timeout_seconds: float = 3.0,
) -> list[OpenWebUIFileCandidate]:
    """Inventory standalone and knowledge-linked file metadata without retrieving content."""
    headers = _openwebui_headers(base_url, api_key)
    files: dict[str, dict[str, object]] = {}
    memberships: dict[str, set[str]] = {}
    base = base_url.rstrip("/")
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds), follow_redirects=False, trust_env=False
    ) as client:
        for page in range(1, max_pages + 1):
            items, total = _openwebui_page(
                client,
                f"{base}/api/v1/files/",
                headers,
                {"page": page, "content": False},
            )
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    files[item["id"]] = item
                    if len(files) >= max_items:
                        break
            if len(files) >= max_items or not items or (total is not None and len(files) >= total):
                break

        linked_seen = 0
        for page in range(1, max_pages + 1):
            items, total = _openwebui_page(
                client,
                f"{base}/api/v1/knowledge/search/files",
                headers,
                {"page": page},
            )
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    continue
                file_id = item["id"]
                if file_id not in files:
                    if len(files) >= max_items:
                        linked_seen += 1
                        continue
                    files[file_id] = item
                collection = item.get("collection")
                if isinstance(collection, dict) and isinstance(collection.get("id"), str):
                    memberships.setdefault(file_id, set()).add(collection["id"])
                linked_seen += 1
            if not items or (total is not None and linked_seen >= total):
                break

    discovered: list[OpenWebUIFileCandidate] = []
    for file_id, item in files.items():
        safe_id = _safe_remote_text(file_id, limit=160)
        filename = _safe_remote_text(item.get("filename"), limit=300)
        if not safe_id or not filename:
            continue
        data = item.get("data")
        status = _safe_remote_text(data.get("status"), limit=40) if isinstance(data, dict) else None
        discovered.append(
            OpenWebUIFileCandidate(
                id=safe_id,
                filename=filename,
                status=status or None,
                knowledge_base_ids=tuple(sorted(memberships.get(file_id, set()))),
            )
        )
    return sorted(discovered, key=lambda item: (item.filename.casefold(), item.id))
