"""Shared synthetic test factories."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from ragscanner.reporting.models import ReportDocument, ReportFinding, ReportProcessingSummary

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


def _report(
    scan_id: str,
    *,
    source_name: str = "Knowledge",
    rule_pack_version: str = "1",
    coverage: str = "assessed",
    findings: list[ReportFinding] | None = None,
    overall: float | None = 80.0,
) -> ReportDocument:
    return ReportDocument(
        generated_at=NOW,
        scan={
            "id": scan_id,
            "type": "static",
            "status": "completed",
            "source_name": source_name,
            "started_at": NOW.isoformat(),
            "completed_at": NOW.isoformat(),
            "rule_pack_version": rule_pack_version,
        },
        processing=ReportProcessingSummary(files_discovered=1, files_scanned=1),
        scores={"overall": overall},
        severity_summary={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        classification_summary={},
        findings=findings or [],
        duplicate_groups=[],
        duplicate_summary={},
        warnings=[],
        skipped_checks=[],
        errors=[],
        configuration={},
        methodology=[],
        limitations=[],
        filters_active=False,
        filter_summary={},
        truncation_notices=[],
        metadata={},
        knowledge_base_mode="collection",
        source_count=1,
        assessment_coverage={"security": {"status": coverage}},
        ingestion_issues=[],
    )


def _finding(fingerprint_character: str, *, severity: str = "medium") -> ReportFinding:
    return ReportFinding(
        id=f"finding-{fingerprint_character}",
        title=f"Finding {fingerprint_character}",
        category="security",
        severity=severity,
        confidence=0.9,
        detection_type="deterministic",
        scanner="static",
        rule_id=f"RULE-{fingerprint_character}",
        rule_version="1",
        evidence="Bounded synthetic evidence.",
        impact="Synthetic impact.",
        recommendation="Synthetic recommendation.",
        first_seen=NOW,
        last_seen=NOW,
        fingerprint=fingerprint_character * 64,
    )


@pytest.fixture
def report() -> Callable[..., ReportDocument]:
    return _report


@pytest.fixture
def finding() -> Callable[..., ReportFinding]:
    return _finding
