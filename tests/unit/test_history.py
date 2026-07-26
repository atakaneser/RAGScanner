from ragscanner.history import compare_scans
from ragscanner.scoring import ScorePolicySnapshot


def test_comparison_classifies_new_resolved_recurring_and_severity_changes(report, finding) -> None:  # type: ignore[no-untyped-def]
    baseline = report("scan-1", findings=[finding("a"), finding("b", severity="low")])
    candidate = report(
        "scan-2", findings=[finding("b", severity="high"), finding("c")], overall=70.0
    )

    comparison = compare_scans(baseline, candidate)

    assert comparison.compatible
    assert [item.fingerprint for item in comparison.new_findings] == ["c" * 64]
    assert [item.fingerprint for item in comparison.resolved_findings] == ["a" * 64]
    assert [item.fingerprint for item in comparison.recurring_findings] == ["b" * 64]
    assert comparison.severity_changes[0].baseline_severity == "low"
    assert comparison.severity_changes[0].candidate_severity == "high"
    assert comparison.score_changes[0].delta == -10.0


def test_comparison_uses_not_observed_when_coverage_or_rule_pack_changes(report, finding) -> None:  # type: ignore[no-untyped-def]
    baseline = report("scan-1", findings=[finding("a")])
    candidate = report("scan-2", coverage="not_assessed", rule_pack_version="2")

    comparison = compare_scans(baseline, candidate)

    assert comparison.resolved_findings == []
    assert [item.fingerprint for item in comparison.not_observed_findings] == ["a" * 64]
    assert len(comparison.warnings) == 2


def test_comparison_refuses_finding_lifecycle_for_different_sources(report, finding) -> None:  # type: ignore[no-untyped-def]
    comparison = compare_scans(
        report("scan-1", findings=[finding("a")]),
        report("scan-2", source_name="Different", findings=[finding("b")]),
    )

    assert not comparison.compatible
    assert comparison.new_findings == []
    assert comparison.resolved_findings == []
    assert "Source identity differs" in comparison.warnings[0]


def test_comparison_warns_when_score_policy_version_changes(report) -> None:  # type: ignore[no-untyped-def]
    def policy(version: str) -> ScorePolicySnapshot:
        return ScorePolicySnapshot(
            policy_version=version,
            base_weights={"security": 0.35, "knowledge_quality": 0.2, "efficiency": 0.15},
            severity_penalties={
                "critical": 25,
                "high": 15,
                "medium": 8,
                "low": 3,
                "info": 1,
            },
            minimum_assessed_dimensions=2,
            critical_security_cap=54.99,
            assessed_dimensions=["security", "knowledge_quality"],
            assessment_coverage_ratio=2 / 3,
            dimension_inputs={},
            formula="test",
        )

    baseline = report("scan-1").model_copy(update={"score_policy_details": policy("1.0.0")})
    candidate = report("scan-2").model_copy(update={"score_policy_details": policy("2.0.0")})

    comparison = compare_scans(baseline, candidate)

    assert any("Score-policy version differs" in warning for warning in comparison.warnings)
