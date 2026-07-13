"""Safe, bounded discovery helpers for the interactive CLI onboarding flow."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx

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


def discover_openwebui_services(
    *,
    endpoints: Iterable[str] = OPENWEBUI_LOOPBACK_ENDPOINTS,
    timeout_seconds: float = 0.75,
) -> list[ServiceCandidate]:
    """Probe fixed loopback health endpoints after the caller has obtained user consent."""
    discovered: list[ServiceCandidate] = []
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for base_url in endpoints:
            health_path = "/health"
            try:
                with client.stream("GET", f"{base_url}{health_path}") as response:
                    if response.status_code == 200:
                        discovered.append(
                            ServiceCandidate(base_url=base_url, health_path=health_path)
                        )
            except httpx.HTTPError:
                continue
    return discovered
