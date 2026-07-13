"""Active black-box security testing contracts; no transport or execution logic."""

from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from ragscanner.domain.enums import (
    DetectionType,
    EvaluationClassification,
    EvaluatorType,
    ExecutionStatus,
    HttpMethod,
    SafetyMode,
    Severity,
    SideEffectRisk,
    TargetType,
)
from ragscanner.domain.helpers import contains_unreferenced_secret, is_secure_secret_reference


class TargetDefinition(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    target_type: TargetType
    base_url: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    request_template: dict[str, Any] = Field(default_factory=dict)
    response_mapping: dict[str, Any] = Field(default_factory=dict)
    authentication_reference: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    delay_seconds: float = Field(default=0.0, ge=0, le=3600)
    max_requests: int = Field(default=100, ge=1, le=100_000)
    verify_tls: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("authentication_reference")
    @classmethod
    def validate_authentication_reference(cls, value: str | None) -> str | None:
        if value is not None and not is_secure_secret_reference(value):
            raise ValueError("authentication_reference must be an external secret reference")
        return value

    @model_validator(mode="after")
    def reject_embedded_secrets(self) -> "TargetDefinition":
        fields = (self.request_template, self.response_mapping, self.headers, self.metadata)
        if any(contains_unreferenced_secret(field) for field in fields):
            raise ValueError("TargetDefinition cannot embed secret values")
        return self


class AuthorizationScope(BaseModel):
    authorized: bool = False
    authorized_by: str | None = None
    authorized_at: AwareDatetime | None = None
    scope_description: str | None = None
    environment: str | None = None
    expires_at: AwareDatetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_explicit_authorization_details(self) -> "AuthorizationScope":
        if self.authorized and not (
            self.authorized_by
            and self.authorized_at
            and self.scope_description
            and self.environment
        ):
            raise ValueError("authorized scope requires actor, time, description, and environment")
        return self

    def is_expired(self, at: datetime | None = None) -> bool:
        reference = at or datetime.now(UTC)
        if reference.tzinfo is None:
            raise ValueError("expiration reference must be timezone-aware")
        return self.expires_at is not None and self.expires_at <= reference

    def is_valid(self, at: datetime | None = None) -> bool:
        return self.authorized and not self.is_expired(at)


class PayloadVariant(BaseModel):
    id: str = Field(min_length=1)
    content: str
    language: str = Field(min_length=2)
    encoding: str = "plain"
    tags: list[str] = Field(default_factory=list)
    safe_for_production: bool = True
    expected_behavior: str = Field(min_length=1)
    placeholders: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityTestCase(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    detection_type: DetectionType
    payloads: list[PayloadVariant] = Field(min_length=1)
    expected_safe_behavior: str = Field(min_length=1)
    unsafe_indicators: list[str] = Field(default_factory=list)
    safe_indicators: list[str] = Field(default_factory=list)
    ambiguous_indicators: list[str] = Field(default_factory=list)
    control_payload: PayloadVariant | None = None
    requires_tool_access: bool = False
    requires_retrieval: bool = False
    languages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    side_effect_risk: SideEffectRisk = SideEffectRisk.NONE
    default_safety_mode: SafetyMode = SafetyMode.SAFE
    remediation: str = "Review target instructions and isolate untrusted context."
    references: list[str] = Field(default_factory=list)
    enabled: bool = True
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_safety_defaults(self) -> "SecurityTestCase":
        if self.default_safety_mode is SafetyMode.SAFE:
            if self.side_effect_risk is SideEffectRisk.DESTRUCTIVE:
                raise ValueError("destructive side effects cannot be safe by default")
            if any(not payload.safe_for_production for payload in self.payloads):
                raise ValueError("unsafe payload cannot be included in a safe-default test")
        return self


class TargetRequest(BaseModel):
    id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    test_case_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    method: HttpMethod
    url: str = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | str | None = None
    timeout_seconds: float = Field(gt=0, le=300)
    created_at: AwareDatetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_secrets(self) -> "TargetRequest":
        if any(
            contains_unreferenced_secret(field)
            for field in (self.headers, self.body, self.metadata)
        ):
            raise ValueError("TargetRequest cannot serialize raw secret values")
        return self


class TargetResponse(BaseModel):
    request_id: str = Field(min_length=1)
    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    latency_ms: float | None = Field(default=None, ge=0)
    received_at: AwareDatetime
    truncated: bool = False
    transport_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_secrets(self) -> "TargetResponse":
        if any(
            contains_unreferenced_secret(field)
            for field in (self.headers, self.body, self.transport_error, self.metadata)
        ):
            raise ValueError("TargetResponse must be redacted before construction")
        return self


class EvaluationResult(BaseModel):
    classification: EvaluationClassification
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)
    matched_indicators: list[str] = Field(default_factory=list)
    manual_review_required: bool = False
    evaluator_type: EvaluatorType
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_secrets(self) -> "EvaluationResult":
        if contains_unreferenced_secret(self.evidence) or contains_unreferenced_secret(
            self.metadata
        ):
            raise ValueError("evaluation evidence cannot contain raw secrets")
        return self


class TestExecution(BaseModel):
    id: str = Field(min_length=1)
    scan_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    test_case_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    request_summary: dict[str, Any] = Field(default_factory=dict)
    response_summary: dict[str, Any] = Field(default_factory=dict)
    evaluation: EvaluationResult | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "TestExecution":
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")
        if any(
            contains_unreferenced_secret(field)
            for field in (self.request_summary, self.response_summary, self.metadata)
        ):
            raise ValueError("execution summaries cannot contain raw secrets")
        return self
