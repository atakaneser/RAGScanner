"""Framework-independent report contracts."""

from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from ragscanner.ai_analysis.models import AIReportAnalysis
from ragscanner.domain import (
    EvaluationClassification,
    Finding,
    Scan,
    ScoreSummary,
    Severity,
    TestExecution,
)
from ragscanner.quality import DuplicateGroup, RAGConfigurationAdvice
from ragscanner.quality.models import ChunkQualityStatistics
from ragscanner.scoring import ScorePolicySnapshot
from ragscanner.security.static_models import StaticScanStatistics

REPORT_SCHEMA_VERSION = "1.4.0"
REPORTER_VERSION = "1.4.0"


class ReportFilter(BaseModel):
    minimum_severity: Severity | None = None
    categories: set[str] = Field(default_factory=set)
    classifications: set[EvaluationClassification] = Field(default_factory=set)
    document_id: str | None = None
    target_id: str | None = None
    rule_ids: set[str] = Field(default_factory=set)
    include_informational: bool = True

    def is_active(self) -> bool:
        return bool(
            self.minimum_severity
            or self.categories
            or self.classifications
            or self.document_id
            or self.target_id
            or self.rule_ids
            or not self.include_informational
        )


class ReportLimits(BaseModel):
    maximum_findings: int = Field(default=500, gt=0, le=100_000)
    maximum_evidence_length: int = Field(default=512, ge=64, le=4_096)
    maximum_duplicate_group_members: int = Field(default=50, gt=0, le=10_000)
    maximum_warnings: int = Field(default=500, gt=0, le=10_000)
    maximum_metadata_fields: int = Field(default=100, gt=0, le=10_000)
    maximum_string_length: int = Field(default=4_096, ge=256, le=100_000)
    maximum_html_size: int = Field(default=5_000_000, ge=10_000, le=100_000_000)
    maximum_json_size: int = Field(default=10_000_000, ge=10_000, le=100_000_000)


class ReportInput(BaseModel):
    scan: Scan
    findings: list[Finding] = Field(default_factory=list)
    executions: list[TestExecution] = Field(default_factory=list)
    scores: ScoreSummary | None = None
    score_policy_details: ScorePolicySnapshot | None = None
    rag_configuration_advice: RAGConfigurationAdvice | None = None
    duplicate_groups: list[DuplicateGroup] = Field(default_factory=list)
    chunk_quality_statistics: ChunkQualityStatistics | None = None
    security_statistics: StaticScanStatistics | None = None
    documents_parsed: int = Field(default=0, ge=0)
    rules_evaluated: list[str] = Field(default_factory=list)
    rules_skipped: list[str] = Field(default_factory=list)
    rules_evaluated_count: int = Field(default=0, ge=0)
    rules_skipped_count: int = Field(default=0, ge=0)
    skipped_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    target_name: str | None = None
    target_capabilities: list[str] = Field(default_factory=list)
    authorization_summary: str | None = None
    configuration_summary: dict[str, Any] = Field(default_factory=dict)
    methodology: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: AwareDatetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    knowledge_base_mode: str = "collection"
    source_count: int = Field(default=0, ge=0)
    assessment_coverage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ingestion_issues: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scan_identity(self) -> "ReportInput":
        if any(item.scan_id != self.scan.id for item in self.executions):
            raise ValueError("all executions must belong to the report scan")
        return self


class ReportFinding(BaseModel):
    id: str
    title: str
    category: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    classification: EvaluationClassification | None = None
    detection_type: str
    scanner: str
    rule_id: str
    rule_version: str
    source: str | None = None
    document_id: str | None = None
    page: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    chunk_id: str | None = None
    target_id: str | None = None
    test_case_id: str | None = None
    execution_id: str | None = None
    evidence: str
    evidence_highlight: str | None = None
    impact: str
    recommendation: str
    references: list[str] = Field(default_factory=list)
    first_seen: AwareDatetime
    last_seen: AwareDatetime
    fingerprint: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportDuplicateGroup(BaseModel):
    id: str
    category: str
    canonical_item_id: str
    related_item_ids: list[str]
    similarity: float = Field(ge=0, le=1)
    estimated_redundant_characters: int = Field(ge=0)
    estimated_redundant_tokens: int = Field(ge=0)
    members_truncated: bool = False


class ReportProcessingSummary(BaseModel):
    files_discovered: int = 0
    files_scanned: int = 0
    files_skipped: int = 0
    documents_parsed: int = 0
    chunks_scanned: int = 0
    active_requests_planned: int = 0
    active_requests_sent: int = 0
    active_requests_failed: int = 0
    rules_evaluated: int = 0
    rules_skipped: int = 0
    warnings: int = 0
    errors: int = 0


class ReportIngestionIssue(BaseModel):
    path: str
    stage: str
    code: str
    message: str
    remediation: str | None = None
    fatal: bool = False


class ReportDocument(BaseModel):
    schema_version: str = REPORT_SCHEMA_VERSION
    reporter_version: str = REPORTER_VERSION
    generated_at: AwareDatetime
    scan: dict[str, Any]
    processing: ReportProcessingSummary
    scores: dict[str, float | None]
    score_policy: str = (
        "RAGScanner product-defined assessed-dimension weighted scores; security receives the "
        "highest weight, and missing dimensions are not assessed."
    )
    score_policy_details: ScorePolicySnapshot | None = None
    rag_configuration_advice: RAGConfigurationAdvice | None = None
    severity_summary: dict[str, int]
    classification_summary: dict[str, int]
    findings: list[ReportFinding]
    duplicate_groups: list[ReportDuplicateGroup]
    duplicate_summary: dict[str, int | float]
    chunk_quality: dict[str, int | float] | None = None
    active_security: dict[str, Any] | None = None
    warnings: list[str]
    skipped_checks: list[str]
    errors: list[str]
    configuration: dict[str, Any]
    methodology: list[str]
    limitations: list[str]
    filters_active: bool
    filter_summary: dict[str, Any]
    truncation_notices: list[str]
    metadata: dict[str, Any]
    knowledge_base_mode: str
    source_count: int
    assessment_coverage: dict[str, dict[str, Any]]
    ingestion_issues: list[ReportIngestionIssue]
    ai_analysis: AIReportAnalysis | None = None
    ai_analysis_error_code: str | None = Field(default=None, max_length=80)
    ai_analysis_error: str | None = Field(default=None, max_length=500)
