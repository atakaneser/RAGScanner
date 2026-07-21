"""Shared static/active findings, scans, and score contracts."""

from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from ragscanner.domain.active import AuthorizationScope
from ragscanner.domain.enums import (
    AnalysisMode,
    DetectionType,
    EvaluationClassification,
    PrivacyMode,
    SafetyMode,
    ScanStatus,
    ScanType,
    Severity,
)
from ragscanner.domain.helpers import contains_unreferenced_secret
from ragscanner.domain.static import SourceLocation


class Finding(BaseModel):
    """Shared base finding for static source and active target observations."""

    id: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    category: str = Field(min_length=1)
    scanner: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    detection_type: DetectionType
    classification: EvaluationClassification | None = None
    source: SourceLocation | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    target_id: str | None = None
    test_case_id: str | None = None
    execution_id: str | None = None
    evidence: str
    impact: str
    recommendation: str
    references: list[str] = Field(default_factory=list)
    first_seen: AwareDatetime
    last_seen: AwareDatetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_finding(self) -> "Finding":
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen cannot be before first_seen")
        active_references = (self.target_id, self.test_case_id, self.execution_id)
        if any(active_references) and not all(active_references):
            raise ValueError("active findings require target, test case, and execution references")
        if contains_unreferenced_secret(self.evidence) or contains_unreferenced_secret(
            self.metadata
        ):
            raise ValueError("findings cannot contain raw secrets")
        return self


class Scan(BaseModel):
    id: str = Field(min_length=1)
    scan_type: ScanType
    source_type: str | None = None
    source_name: str | None = None
    target_id: str | None = None
    status: ScanStatus = ScanStatus.PENDING
    mode: AnalysisMode = AnalysisMode.OFFLINE
    safety_mode: SafetyMode = SafetyMode.SAFE
    authorization_scope: AuthorizationScope | None = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    scanner_version: str = Field(min_length=1)
    rule_pack_version: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    privacy_mode: PrivacyMode = PrivacyMode.LOCAL_ONLY
    files_discovered: int = Field(default=0, ge=0)
    files_scanned: int = Field(default=0, ge=0)
    files_skipped: int = Field(default=0, ge=0)
    chunks_scanned: int = Field(default=0, ge=0)
    requests_planned: int = Field(default=0, ge=0)
    requests_sent: int = Field(default=0, ge=0)
    requests_failed: int = Field(default=0, ge=0)
    finding_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scan(self) -> "Scan":
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")
        if any(count < 0 for count in self.finding_counts.values()):
            raise ValueError("finding counts cannot be negative")
        if self.scan_type in {ScanType.ACTIVE, ScanType.COMBINED}:
            if not self.target_id:
                raise ValueError("active scans require target_id")
            if self.authorization_scope is None or not self.authorization_scope.is_valid():
                raise ValueError("active scans require explicit, unexpired authorization")
        if contains_unreferenced_secret(self.metadata):
            raise ValueError("scan metadata cannot contain raw secrets")
        return self


class ScoreSummary(BaseModel):
    overall: float | None = Field(default=None, ge=0, le=100)
    consistency: float | None = Field(default=None, ge=0, le=100)
    knowledge_quality: float | None = Field(default=None, ge=0, le=100)
    retrieval_quality: float | None = Field(default=None, ge=0, le=100)
    answer_reliability: float | None = Field(default=None, ge=0, le=100)
    security: float | None = Field(default=None, ge=0, le=100)
    freshness: float | None = Field(default=None, ge=0, le=100)
    efficiency: float | None = Field(default=None, ge=0, le=100)
    rag_rot: float | None = Field(default=None, ge=0, le=100)
