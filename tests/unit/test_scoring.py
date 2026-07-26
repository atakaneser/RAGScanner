"""Versioned score policy, monotonicity, coverage, and cap tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from ragscanner.domain import (
    Chunk,
    DetectionType,
    EvaluationClassification,
    Finding,
    Severity,
    SourceLocation,
)
from ragscanner.quality import ChunkQualityResult, ChunkQualityScore
from ragscanner.quality.models import ChunkQualityStatistics
from ragscanner.scoring import ScoreCalculator, ScoringPolicy

NOW = datetime(2026, 7, 22, tzinfo=UTC)


def finding(identifier: str, severity: Severity) -> Finding:
    return Finding(
        id=identifier,
        fingerprint=(identifier.encode().hex() + "0" * 64)[:64],
        category="prompt_injection",
        scanner="static_security_scanner",
        rule_id=f"STATIC-{identifier.upper()}",
        rule_version="1.0.0",
        title="Synthetic security finding",
        description="Synthetic score fixture",
        severity=severity,
        confidence=1,
        detection_type=DetectionType.DETERMINISTIC,
        classification=EvaluationClassification.CONFIRMED,
        evidence="Synthetic evidence",
        impact="Synthetic impact",
        recommendation="Synthetic recommendation",
        first_seen=NOW,
        last_seen=NOW,
    )


def chunk(identifier: str, tokens: int) -> Chunk:
    return Chunk(
        id=identifier,
        document_id="document",
        index=0,
        content="synthetic",
        normalized_content="synthetic",
        content_hash="0" * 64,
        token_count=tokens,
        character_count=9,
        source=SourceLocation(
            source_id="source",
            source_type="filesystem",
            source_name="fixture",
            source_path="fixture.md",
        ),
    )


def quality(scores: dict[str, float]) -> ChunkQualityResult:
    return ChunkQualityResult(
        scores={
            identifier: ChunkQualityScore(
                overall=value,
                size_quality=value,
                structural_integrity=value,
                information_density=value,
                overlap_efficiency=value,
                source_mapping_quality=value,
                extraction_quality=value,
            )
            for identifier, value in scores.items()
        },
        statistics=ChunkQualityStatistics(
            total_chunks=len(scores),
            oversized_chunks=0,
            undersized_chunks=0,
            empty_chunks=0,
            structurally_broken_chunks=0,
            average_chunk_tokens=100,
            median_chunk_tokens=100,
            estimated_redundant_tokens=0,
        ),
        scanner_name="chunk_quality_scanner",
        scanner_version="1.3.0",
    )


def calculate(findings: list[Finding]):  # type: ignore[no-untyped-def]
    return ScoreCalculator().calculate(
        findings=findings,
        chunks=[],
        quality_result=None,
        exact_result=None,
        near_result=None,
        security_assessed=True,
        document_count=1,
    )


def test_security_penalties_are_monotonic_and_policy_is_reproducible() -> None:
    clean = calculate([])
    low = calculate([finding("low", Severity.LOW)])
    high = calculate([finding("high", Severity.HIGH)])

    assert clean.summary.security == 100
    assert clean.summary.security > low.summary.security > high.summary.security
    assert clean.policy.policy_version == "1.0.0"
    assert clean.policy.dimension_inputs["documents"] == 1
    assert clean.policy.assessed_dimensions == ["security"]


def test_critical_security_finding_caps_overall_in_red_band() -> None:
    result = ScoreCalculator().calculate(
        findings=[finding("critical", Severity.CRITICAL)],
        chunks=[chunk("large", 1_000)],
        quality_result=quality({"large": 100}),
        exact_result=None,
        near_result=None,
        security_assessed=True,
        document_count=1,
    )

    assert result.summary.overall == 54.99
    assert result.policy.critical_cap_applied is True


def test_chunk_quality_uses_token_weighting_instead_of_chunk_count() -> None:
    result = ScoreCalculator().calculate(
        findings=[],
        chunks=[chunk("large", 900), chunk("small", 100)],
        quality_result=quality({"large": 50, "small": 100}),
        exact_result=None,
        near_result=None,
        security_assessed=False,
        document_count=1,
    )

    assert result.summary.knowledge_quality == 55


def test_minimum_dimension_coverage_can_withhold_overall() -> None:
    result = ScoreCalculator(ScoringPolicy(minimum_assessed_dimensions=2)).calculate(
        findings=[],
        chunks=[],
        quality_result=None,
        exact_result=None,
        near_result=None,
        security_assessed=True,
        document_count=1,
    )

    assert result.summary.security == 100
    assert result.summary.overall is None
    assert result.policy.assessment_coverage_ratio == pytest.approx(1 / 3)


def test_policy_rejects_missing_dimensions_and_invalid_penalties() -> None:
    with pytest.raises(ValidationError):
        ScoringPolicy(weights={"security": 1})
    with pytest.raises(ValidationError):
        ScoringPolicy(severity_penalties={Severity.HIGH: 1})
