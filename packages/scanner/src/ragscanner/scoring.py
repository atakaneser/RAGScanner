"""Versioned, coverage-aware product scoring for deterministic scans."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ragscanner.domain import Chunk, Finding, ScoreSummary, Severity
from ragscanner.quality.models import ChunkQualityResult, DuplicateScanResult

_DIMENSIONS = frozenset({"security", "knowledge_quality", "efficiency"})


class ScoringPolicy(BaseModel):
    """Configurable product policy; it is not a scientific quality standard."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0.0", pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "security": 0.35,
            "knowledge_quality": 0.20,
            "efficiency": 0.15,
        }
    )
    severity_penalties: dict[Severity, float] = Field(
        default_factory=lambda: {
            Severity.CRITICAL: 25.0,
            Severity.HIGH: 15.0,
            Severity.MEDIUM: 8.0,
            Severity.LOW: 3.0,
            Severity.INFO: 1.0,
        }
    )
    critical_security_cap: float | None = Field(default=54.99, ge=0, le=100)
    minimum_assessed_dimensions: int = Field(default=2, ge=1, le=3)

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != _DIMENSIONS:
            raise ValueError(
                "score weights must define security, knowledge_quality, and efficiency"
            )
        if any(weight < 0 or weight > 1 for weight in value.values()) or not any(value.values()):
            raise ValueError("score weights must be between zero and one with a positive total")
        return value

    @model_validator(mode="after")
    def validate_penalties(self) -> "ScoringPolicy":
        if set(self.severity_penalties) != set(Severity):
            raise ValueError("severity penalties must define every severity")
        if any(value < 0 or value > 100 for value in self.severity_penalties.values()):
            raise ValueError("severity penalties must be between zero and one hundred")
        return self


class ScorePolicySnapshot(BaseModel):
    policy_version: str
    base_weights: dict[str, float]
    severity_penalties: dict[str, float]
    critical_security_cap: float | None
    minimum_assessed_dimensions: int
    assessed_dimensions: list[str]
    assessment_coverage_ratio: float = Field(ge=0, le=1)
    critical_cap_applied: bool = False
    dimension_inputs: dict[str, Any] = Field(default_factory=dict)
    formula: str
    calibration_status: str = "provisional_unvalidated"


class ScoringResult(BaseModel):
    summary: ScoreSummary
    policy: ScorePolicySnapshot


class ScoreCalculator:
    """Pure calculator with reproducible inputs and an auditable policy snapshot."""

    def __init__(self, policy: ScoringPolicy | None = None) -> None:
        self.policy = policy or ScoringPolicy()

    def calculate(
        self,
        *,
        findings: list[Finding],
        chunks: list[Chunk],
        quality_result: ChunkQualityResult | None,
        exact_result: DuplicateScanResult | None,
        near_result: DuplicateScanResult | None,
        security_assessed: bool,
        document_count: int,
    ) -> ScoringResult:
        security_findings = [item for item in findings if item.scanner == "static_security_scanner"]
        security: float | None = None
        if security_assessed:
            penalty = sum(
                self.policy.severity_penalties[item.severity] * item.confidence
                for item in security_findings
            )
            security = max(0.0, 100.0 - penalty)

        knowledge: float | None = None
        if quality_result is not None and quality_result.scores:
            token_weights = {chunk.id: max(1, chunk.token_count) for chunk in chunks}
            weighted = [
                (score.overall, token_weights.get(chunk_id, 1))
                for chunk_id, score in quality_result.scores.items()
            ]
            knowledge = sum(value * weight for value, weight in weighted) / sum(
                weight for _value, weight in weighted
            )

        duplicate_percentages = [
            item.statistics.duplicate_content_percentage
            for item in (exact_result, near_result)
            if item is not None
        ]
        efficiency = max(0.0, 100.0 - max(duplicate_percentages)) if duplicate_percentages else None
        values = {
            "security": security,
            "knowledge_quality": knowledge,
            "efficiency": efficiency,
        }
        assessed = [name for name, value in values.items() if value is not None]
        weighted_values = [
            (value, self.policy.weights[name])
            for name, value in values.items()
            if value is not None and self.policy.weights[name] > 0
        ]
        overall = None
        if (
            len(assessed) >= self.policy.minimum_assessed_dimensions
            and weighted_values
            and sum(weight for _value, weight in weighted_values) > 0
        ):
            overall = sum(value * weight for value, weight in weighted_values) / sum(
                weight for _value, weight in weighted_values
            )

        critical_present = any(item.severity is Severity.CRITICAL for item in security_findings)
        cap_applied = bool(
            overall is not None
            and critical_present
            and self.policy.critical_security_cap is not None
            and overall > self.policy.critical_security_cap
        )
        if cap_applied:
            overall = self.policy.critical_security_cap

        summary = ScoreSummary(
            overall=overall,
            knowledge_quality=knowledge,
            security=security,
            efficiency=efficiency,
        )
        snapshot = ScorePolicySnapshot(
            policy_version=self.policy.version,
            base_weights=dict(self.policy.weights),
            severity_penalties={
                severity.value: value for severity, value in self.policy.severity_penalties.items()
            },
            critical_security_cap=self.policy.critical_security_cap,
            minimum_assessed_dimensions=self.policy.minimum_assessed_dimensions,
            assessed_dimensions=assessed,
            assessment_coverage_ratio=len(assessed) / len(_DIMENSIONS),
            critical_cap_applied=cap_applied,
            dimension_inputs={
                "documents": document_count,
                "chunks": len(chunks),
                "security_findings": len(security_findings),
                "security_findings_per_document": len(security_findings) / max(1, document_count),
                "quality_chunks_scored": len(quality_result.scores)
                if quality_result is not None
                else 0,
                "exact_duplicate_percentage": exact_result.statistics.duplicate_content_percentage
                if exact_result is not None
                else None,
                "near_duplicate_percentage": near_result.statistics.duplicate_content_percentage
                if near_result is not None
                else None,
            },
            formula=(
                "Severity-and-confidence security penalties; token-weighted chunk quality; "
                "maximum observed duplicate percentage; normalized assessed-dimension weights."
            ),
        )
        return ScoringResult(summary=summary, policy=snapshot)
