from ragscanner.reporting import without_removed_consistency


def test_historical_consistency_results_are_removed_and_score_is_recomputed(
    report, finding
) -> None:  # type: ignore[no-untyped-def]
    security_finding = finding("a").model_copy(update={"scanner": "static_security_scanner"})
    consistency_finding = finding("b").model_copy(
        update={
            "scanner": "consistency_scanner",
            "category": "consistency_conflict",
            "classification": "confirmed",
            "severity": "high",
        }
    )
    historical = report("scan-1", findings=[security_finding, consistency_finding]).model_copy(
        update={
            "scores": {
                "overall": 26.4,
                "security": 80.0,
                "consistency": 0.0,
                "knowledge_quality": 90.0,
                "efficiency": 100.0,
            },
            "severity_summary": {"critical": 0, "high": 1, "medium": 1, "low": 0, "info": 0},
            "classification_summary": {"confirmed": 1},
            "assessment_coverage": {
                "security": {"status": "assessed"},
                "consistency": {"status": "assessed"},
                "version_conflict": {"status": "partial"},
            },
        }
    )

    displayed = without_removed_consistency(historical)

    assert [item.id for item in displayed.findings] == [security_finding.id]
    assert displayed.scores == {
        "overall": 86.84931506849315,
        "security": 80.0,
        "knowledge_quality": 90.0,
        "efficiency": 100.0,
    }
    assert displayed.severity_summary["high"] == 0
    assert displayed.classification_summary["confirmed"] == 0
    assert "consistency" not in displayed.assessment_coverage
    assert displayed.assessment_coverage["version_conflict"]["status"] == "not_assessed"


def test_current_report_is_returned_unchanged(report) -> None:  # type: ignore[no-untyped-def]
    current = report("scan-1")

    assert without_removed_consistency(current) is current
