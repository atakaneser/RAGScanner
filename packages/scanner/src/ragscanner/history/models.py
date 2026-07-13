"""Stable view models for local scan history and comparison."""

from pydantic import AwareDatetime, BaseModel, Field


class ScanHistorySummary(BaseModel):
    history_id: str
    scan_id: str
    scan_type: str
    status: str
    source_name: str | None = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    overall_score: float | None = Field(default=None, ge=0, le=100)
    finding_count: int = Field(ge=0)
    schema_version: str
    created_at: AwareDatetime


class ScanHistoryPage(BaseModel):
    items: list[ScanHistorySummary]
    total: int = Field(ge=0)
    limit: int = Field(gt=0, le=200)
    offset: int = Field(ge=0)


class FindingChange(BaseModel):
    fingerprint: str
    rule_id: str
    title: str
    baseline_severity: str | None = None
    candidate_severity: str | None = None


class ScoreChange(BaseModel):
    name: str
    baseline: float | None = None
    candidate: float | None = None
    delta: float | None = None


class ScanComparison(BaseModel):
    baseline_scan_id: str
    candidate_scan_id: str
    compatible: bool
    warnings: list[str] = Field(default_factory=list)
    new_findings: list[FindingChange] = Field(default_factory=list)
    resolved_findings: list[FindingChange] = Field(default_factory=list)
    not_observed_findings: list[FindingChange] = Field(default_factory=list)
    recurring_findings: list[FindingChange] = Field(default_factory=list)
    severity_changes: list[FindingChange] = Field(default_factory=list)
    score_changes: list[ScoreChange] = Field(default_factory=list)
