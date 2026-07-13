from ragscanner.history import compare_scans


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
