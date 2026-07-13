"""Pure hashing, truncation, normalization, and redaction helpers."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"
TRUNCATED = "…[TRUNCATED]"
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "cookie",
    "set-cookie",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|(?:access[_-]?)?token|secret|password)\s*[:=]\s*['\"]?[^\s,'\"]{8,}"
    ),
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(authorization|api[_-]?key|(?:access[_-]?)?token|secret|password|credential|cookie)"
)
_REFERENCE_PATTERN = re.compile(
    r"^(env|keychain|secret-manager|vault|file-secret):[A-Za-z0-9_./:@-]+$"
)


def normalize_control_characters(value: str) -> str:
    """Return a copy with unsafe control characters replaced, preserving whitespace controls."""

    return "".join(
        character
        if character in "\n\r\t" or not unicodedata.category(character).startswith("C")
        else "�"
        for character in value
    )


def mask_secret_like_values(value: str) -> str:
    """Return a new string with common secret-like values masked."""

    masked = value
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(REDACTED, masked)
    return masked


def truncate_text(value: str, limit: int, *, marker: str = TRUNCATED) -> str:
    if limit < len(marker):
        raise ValueError("limit must be at least as long as the truncation marker")
    normalized = normalize_control_characters(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - len(marker)] + marker


def truncate_evidence(value: str, limit: int = 512) -> str:
    return truncate_text(mask_secret_like_values(value), limit)


def truncate_response_body(value: str, limit: int = 4096) -> str:
    return truncate_text(mask_secret_like_values(value), limit)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a redacted copy; never mutate the caller's mapping."""

    return {
        name: REDACTED
        if name.casefold() in SENSITIVE_HEADER_NAMES
        else truncate_text(mask_secret_like_values(value), 1024)
        for name, value in headers.items()
    }


def is_secure_secret_reference(value: str) -> bool:
    return bool(_REFERENCE_PATTERN.fullmatch(value))


def contains_unreferenced_secret(value: Any, *, parent_key: str = "") -> bool:
    """Conservatively reject embedded credentials while allowing opaque references."""

    if isinstance(value, str):
        if is_secure_secret_reference(value) or value == REDACTED:
            return False
        if _SECRET_KEY_PATTERN.search(parent_key):
            return bool(value)
        return mask_secret_like_values(value) != value
    if isinstance(value, Mapping):
        return any(
            contains_unreferenced_secret(item, parent_key=str(key)) for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return any(contains_unreferenced_secret(item, parent_key=parent_key) for item in value)
    return False


def _canonical_hash(namespace: str, payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        {"namespace": namespace, **payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def document_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chunk_fingerprint(
    *, document_id: str, index: int, normalized_content: str, source_id: str
) -> str:
    return _canonical_hash(
        "chunk:v1",
        {
            "document_id": document_id,
            "index": index,
            "normalized_content": normalized_content,
            "source_id": source_id,
        },
    )


def finding_fingerprint(
    *,
    rule_id: str,
    rule_version: str,
    source_id: str | None,
    document_id: str | None,
    chunk_id: str | None,
    target_id: str | None,
    test_case_id: str | None,
    evidence: str,
) -> str:
    return _canonical_hash(
        "finding:v1",
        {
            "rule_id": rule_id,
            "rule_version": rule_version,
            "source_id": source_id,
            "document_id": document_id,
            "chunk_id": chunk_id,
            "target_id": target_id,
            "test_case_id": test_case_id,
            "evidence": normalize_control_characters(evidence),
        },
    )


def test_execution_fingerprint(
    *, target_id: str, test_case_id: str, payload_id: str, scan_id: str
) -> str:
    return _canonical_hash(
        "test-execution:v1",
        {
            "target_id": target_id,
            "test_case_id": test_case_id,
            "payload_id": payload_id,
            "scan_id": scan_id,
        },
    )
