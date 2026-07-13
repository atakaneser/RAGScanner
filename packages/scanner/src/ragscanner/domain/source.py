"""Vendor-neutral contracts for reading static knowledge sources."""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from ragscanner.domain.helpers import (
    contains_unreferenced_secret,
    is_secure_secret_reference,
    mask_secret_like_values,
)


class SourceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class SourceChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class SourceErrorCategory(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    MALFORMED_RESPONSE = "malformed_response"
    CONTENT_TOO_LARGE = "content_too_large"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


def _reject_secrets(value: dict[str, Any]) -> dict[str, Any]:
    if contains_unreferenced_secret(value):
        raise ValueError("raw credentials are not allowed; use a secure reference")
    return value


class SourceWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    item_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)


class SourceCapabilities(BaseModel):
    discover_documents: bool = False
    read_document_content: bool = False
    read_metadata: bool = False
    preserve_page_locations: bool = False
    preserve_chunk_locations: bool = False
    incremental_sync: bool = False
    change_detection: bool = False
    delete_detection: bool = False
    remote: bool = False
    read_only: bool = True


class SourceDescriptor(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    capabilities: SourceCapabilities
    configuration_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("configuration_reference")
    @classmethod
    def validate_configuration_reference(cls, value: str | None) -> str | None:
        if value is not None and not is_secure_secret_reference(value):
            raise ValueError("configuration_reference must be an approved secure reference")
        return value

    _safe_metadata = field_validator("metadata")(_reject_secrets)


class SourceItem(BaseModel):
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    path: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    created_at: AwareDatetime | None = None
    modified_at: AwareDatetime | None = None
    version: str | None = None
    etag: str | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)


class SourceContent(BaseModel):
    item: SourceItem
    content_bytes: bytes
    content_type: str = Field(min_length=1)
    encoding: str | None = None
    retrieved_at: AwareDatetime
    checksum: str | None = None
    truncated: bool = False
    limit_bytes: int | None = Field(default=None, gt=0)
    size_bytes: int = Field(default=0, ge=0)
    warnings: list[SourceWarning] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)

    @model_validator(mode="after")
    def validate_limit(self) -> "SourceContent":
        actual_size = len(self.content_bytes)
        if self.size_bytes not in {0, actual_size}:
            raise ValueError("size_bytes must match content_bytes length")
        object.__setattr__(self, "size_bytes", actual_size)
        if self.limit_bytes is not None and self.size_bytes > self.limit_bytes:
            raise ValueError("content exceeds limit_bytes")
        if self.truncated and self.limit_bytes is None:
            raise ValueError("truncated content must record limit_bytes")
        return self


class SourceCursor(BaseModel):
    source_id: str = Field(min_length=1)
    cursor_value: str = Field(min_length=1)
    created_at: AwareDatetime
    expires_at: AwareDatetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)

    @model_validator(mode="after")
    def validate_expiry(self) -> "SourceCursor":
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self


class SourceChange(BaseModel):
    source_id: str = Field(min_length=1)
    item_id: str | None = None
    external_id: str | None = None
    change_type: SourceChangeType
    detected_at: AwareDatetime
    previous_version: str | None = None
    current_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)

    @model_validator(mode="after")
    def validate_identity(self) -> "SourceChange":
        if self.item_id is None and self.external_id is None:
            raise ValueError("a change needs item_id or external_id")
        return self


class SourceHealth(BaseModel):
    status: SourceHealthStatus
    checked_at: AwareDatetime
    latency_ms: float | None = Field(default=None, ge=0)
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    _safe_details = field_validator("details")(_reject_secrets)


class SourcePage(BaseModel):
    items: list[SourceItem] = Field(default_factory=list)
    next_cursor: SourceCursor | None = None
    has_more: bool = False
    warnings: list[SourceWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pagination(self) -> "SourcePage":
        if self.has_more and self.next_cursor is None:
            raise ValueError("has_more requires next_cursor")
        return self


class SourceChangePage(BaseModel):
    items: list[SourceChange] = Field(default_factory=list)
    next_cursor: SourceCursor | None = None
    has_more: bool = False
    warnings: list[SourceWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pagination(self) -> "SourceChangePage":
        if self.has_more and self.next_cursor is None:
            raise ValueError("has_more requires next_cursor")
        return self


class SourceErrorDetail(BaseModel):
    category: SourceErrorCategory
    message: str = Field(min_length=1)
    retryable: bool = False
    source_id: str | None = None
    item_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _safe_metadata = field_validator("metadata")(_reject_secrets)

    @field_validator("message")
    @classmethod
    def mask_message_secrets(cls, value: str) -> str:
        return mask_secret_like_values(value)


class SourceError(Exception):
    """Typed connector failure whose string representation is secret-safe."""

    def __init__(self, detail: SourceErrorDetail) -> None:
        safe_message = mask_secret_like_values(detail.message)
        self.detail = detail.model_copy(update={"message": safe_message})
        super().__init__(safe_message)

    def __repr__(self) -> str:
        return f"SourceError(category={self.detail.category.value!r}, message={str(self)!r})"


@runtime_checkable
class SourceConnector(Protocol):
    """Read-only async port. Implementations must honor task cancellation and byte limits."""

    async def describe(self) -> SourceDescriptor: ...

    async def health_check(self) -> SourceHealth: ...

    async def list_items(self, cursor: SourceCursor | None, limit: int) -> SourcePage: ...

    async def get_item(self, item_id: str) -> SourceItem: ...

    async def get_content(self, item_id: str, max_bytes: int) -> SourceContent: ...

    async def detect_changes(self, cursor: SourceCursor | None) -> SourceChangePage: ...
