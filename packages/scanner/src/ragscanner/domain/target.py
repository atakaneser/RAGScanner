"""Vendor-neutral target adapter contracts; no transport or evaluation logic."""

import re
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from ragscanner.domain.active import PayloadVariant, SecurityTestCase
from ragscanner.domain.enums import HttpMethod, SafetyMode, TargetType
from ragscanner.domain.helpers import (
    REDACTED,
    contains_unreferenced_secret,
    is_secure_secret_reference,
    mask_secret_like_values,
    redact_headers,
    truncate_evidence,
    truncate_response_body,
)


class TargetHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class TargetErrorCategory(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    MALFORMED_RESPONSE = "malformed_response"
    UNSUPPORTED = "unsupported"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"
    TLS_ERROR = "tls_error"
    UNSAFE_OPERATION_BLOCKED = "unsafe_operation_blocked"
    UNKNOWN = "unknown"


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if contains_unreferenced_secret(value):
        raise ValueError("raw credentials are not allowed in metadata")
    return value


def _redact_value(value: Any, *, key: str = "") -> Any:
    sensitive = any(
        part in key.casefold()
        for part in ("authorization", "cookie", "secret", "token", "password", "api_key", "apikey")
    )
    if sensitive and value not in (None, "", REDACTED):
        return REDACTED
    if isinstance(value, str):
        return truncate_response_body(value)
    if isinstance(value, dict):
        return {
            str(item_key): _redact_value(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact_value(item, key=key) for item in value]
    return value


def _redact_error_text(value: str) -> str:
    redacted = mask_secret_like_values(value)
    redacted = re.sub(
        r"(?i)\b(cookie|set-cookie)\s*[:=]\s*[^\s,;]+",
        rf"\1={REDACTED}",
        redacted,
    )
    return re.sub(
        r"(?i)([?&](?:api[_-]?key|token|secret|password)=)[^&\s]+",
        rf"\1{REDACTED}",
        redacted,
    )


class TargetCapabilities(BaseModel):
    chat_completion: bool = False
    retrieval_present: bool = False
    citations_present: bool = False
    source_documents_present: bool = False
    streaming: bool = False
    tool_calls: bool = False
    function_calls: bool = False
    conversation_state: bool = False
    custom_headers: bool = False
    structured_output: bool = False
    request_cancellation: bool = False
    rate_limit_headers: bool = False
    model_discovery: bool = False
    safe_test_mode: bool = True
    destructive_test_mode: bool = False
    remote: bool = True


class TargetDescriptor(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    target_type: TargetType
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    capabilities: TargetCapabilities
    configuration_reference: str
    default_timeout_seconds: float = Field(default=30, gt=0, le=300)
    default_delay_seconds: float = Field(default=0, ge=0)
    default_max_requests: int = Field(default=100, gt=0)
    verify_tls: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("configuration_reference")
    @classmethod
    def validate_reference(cls, value: str) -> str:
        if not is_secure_secret_reference(value):
            raise ValueError("configuration_reference must be an external secure reference")
        return value

    _validate_metadata = field_validator("metadata")(_safe_metadata)


class TargetHealth(BaseModel):
    status: TargetHealthStatus
    checked_at: AwareDatetime
    latency_ms: float | None = Field(default=None, ge=0)
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    _validate_details = field_validator("details")(_safe_metadata)


class TargetInvocation(BaseModel):
    id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    test_case_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    conversation_id: str | None = None
    method: HttpMethod
    path: str = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | str | None = None
    timeout_seconds: float = Field(gt=0, le=300)
    created_at: AwareDatetime
    safety_mode: SafetyMode = SafetyMode.SAFE
    request_budget_cost: int = Field(default=1, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_embedded_secrets(self) -> "TargetInvocation":
        if any(
            contains_unreferenced_secret(value)
            for value in (self.path, self.headers, self.body, self.metadata)
        ):
            raise ValueError("TargetInvocation cannot embed credentials or authorization values")
        return self

    @field_serializer("headers")
    def serialize_headers(self, value: dict[str, str]) -> dict[str, str]:
        return redact_headers(value)


class TargetCitation(BaseModel):
    reference: str = Field(min_length=1)
    excerpt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reference", "excerpt")
    @classmethod
    def make_excerpt_safe(cls, value: str) -> str:
        return truncate_evidence(value)

    _validate_metadata = field_validator("metadata")(_safe_metadata)


class TargetSourceDocument(BaseModel):
    id: str | None = None
    title: str | None = None
    excerpt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "title", "excerpt")
    @classmethod
    def make_excerpt_safe(cls, value: str | None) -> str | None:
        return None if value is None else truncate_evidence(value)

    _validate_metadata = field_validator("metadata")(_safe_metadata)


class TargetToolCall(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    canary_or_noop: bool = False

    @field_validator("arguments", mode="before")
    @classmethod
    def redact_arguments(cls, value: Any) -> Any:
        return _redact_value(value)


class TargetFunctionCall(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    canary_or_noop: bool = False

    @field_validator("arguments", mode="before")
    @classmethod
    def redact_arguments(cls, value: Any) -> Any:
        return _redact_value(value)


class TargetObservation(BaseModel):
    invocation_id: str = Field(min_length=1)
    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    structured_body: dict[str, Any] | list[Any] | None = None
    citations: list[TargetCitation] = Field(default_factory=list)
    source_documents: list[TargetSourceDocument] = Field(default_factory=list)
    tool_calls: list[TargetToolCall] = Field(default_factory=list)
    function_calls: list[TargetFunctionCall] = Field(default_factory=list)
    model_name: str | None = None
    finish_reason: str | None = None
    external_session_id: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    received_at: AwareDatetime
    truncated: bool = False
    transport_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("headers", mode="before")
    @classmethod
    def redact_observation_headers(cls, value: dict[str, str]) -> dict[str, str]:
        return redact_headers(value)

    @field_validator("body", "transport_error", mode="before")
    @classmethod
    def redact_text(cls, value: str | None) -> str | None:
        return None if value is None else truncate_response_body(value)

    @field_validator("structured_body", mode="before")
    @classmethod
    def redact_structured_body(cls, value: Any) -> Any:
        return _redact_value(value)

    _validate_metadata = field_validator("metadata")(_safe_metadata)


class TargetSession(BaseModel):
    id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    external_session_id: str | None = None
    created_at: AwareDatetime
    expires_at: AwareDatetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _validate_metadata = field_validator("metadata")(_safe_metadata)

    @model_validator(mode="after")
    def validate_expiry(self) -> "TargetSession":
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self


class TargetBudget(BaseModel):
    max_requests: int = Field(gt=0)
    requests_used: int = Field(default=0, ge=0)
    max_duration_seconds: float = Field(gt=0)
    elapsed_seconds: float = Field(default=0, ge=0)
    max_failures: int = Field(gt=0)
    failures: int = Field(default=0, ge=0)
    rate_limit_delay_seconds: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    _validate_metadata = field_validator("metadata")(_safe_metadata)

    def is_exhausted(self, request_cost: int = 1) -> bool:
        if request_cost <= 0:
            raise ValueError("request_cost must be positive")
        return (
            self.requests_used + request_cost > self.max_requests
            or self.elapsed_seconds >= self.max_duration_seconds
            or self.failures >= self.max_failures
        )


class TargetErrorDetail(BaseModel):
    category: TargetErrorCategory
    message: str = Field(min_length=1)
    retryable: bool = False
    target_id: str | None = None
    invocation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _validate_metadata = field_validator("metadata")(_safe_metadata)

    @field_validator("message")
    @classmethod
    def redact_message(cls, value: str) -> str:
        return _redact_error_text(value)


class TargetError(Exception):
    def __init__(self, detail: TargetErrorDetail) -> None:
        self.detail = detail
        super().__init__(detail.message)

    def __repr__(self) -> str:
        return f"TargetError(category={self.detail.category.value!r}, message={str(self)!r})"


@runtime_checkable
class TargetAdapter(Protocol):
    """Async active-target port. It transports tests but never evaluates vulnerabilities."""

    async def describe(self) -> TargetDescriptor: ...

    async def health_check(self) -> TargetHealth: ...

    async def prepare_invocation(
        self,
        test_case: SecurityTestCase,
        payload: PayloadVariant,
        session: TargetSession | None,
        safety_mode: SafetyMode = SafetyMode.SAFE,
    ) -> TargetInvocation: ...

    async def invoke(self, invocation: TargetInvocation) -> TargetObservation: ...

    async def create_session(self) -> TargetSession | None: ...

    async def close_session(self, session: TargetSession) -> None: ...

    async def discover_models(self) -> list[str]: ...

    async def cancel(self, invocation_id: str) -> bool: ...
