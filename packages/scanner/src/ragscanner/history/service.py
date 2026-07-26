"""Pure, deterministic scan comparison over versioned report contracts."""

from ragscanner.history.models import FindingChange, ScanComparison, ScoreChange
from ragscanner.reporting.models import ReportDocument, ReportFinding


def _change(
    finding: ReportFinding,
    *,
    baseline_severity: str | None = None,
    candidate_severity: str | None = None,
) -> FindingChange:
    return FindingChange(
        fingerprint=finding.fingerprint,
        rule_id=finding.rule_id,
        title=finding.title,
        baseline_severity=baseline_severity,
        candidate_severity=candidate_severity,
    )


def _coverage_signature(report: ReportDocument) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (name, str(value.get("status", "unknown")))
            for name, value in report.assessment_coverage.items()
        )
    )


def _score_policy_version(report: ReportDocument) -> str | None:
    if report.score_policy_details is not None:
        return report.score_policy_details.policy_version
    value = report.configuration.get("score_policy_version")
    return str(value) if value is not None else None


def compare_scans(baseline: ReportDocument, candidate: ReportDocument) -> ScanComparison:
    """Classify finding and score changes without inferring causation."""
    warnings: list[str] = []
    same_source = baseline.scan.get("source_name") == candidate.scan.get("source_name")
    same_type = baseline.scan.get("type") == candidate.scan.get("type")
    compatible = same_source and same_type
    if not same_source:
        warnings.append("Source identity differs; finding lifecycle comparison was refused.")
    if not same_type:
        warnings.append("Scan type differs; finding lifecycle comparison was refused.")

    baseline_by_fingerprint = {item.fingerprint: item for item in baseline.findings}
    candidate_by_fingerprint = {item.fingerprint: item for item in candidate.findings}
    if not compatible:
        return ScanComparison(
            baseline_scan_id=str(baseline.scan["id"]),
            candidate_scan_id=str(candidate.scan["id"]),
            compatible=False,
            warnings=warnings,
            score_changes=_score_changes(baseline, candidate),
        )

    coverage_equal = _coverage_signature(baseline) == _coverage_signature(candidate)
    rule_pack_equal = baseline.scan.get("rule_pack_version") == candidate.scan.get(
        "rule_pack_version"
    )
    if not coverage_equal:
        warnings.append(
            "Assessment coverage differs; missing baseline findings are classified as not observed."
        )
    if not rule_pack_equal:
        warnings.append(
            "Rule-pack version differs; missing baseline findings are classified as not observed."
        )
    score_policy_equal = _score_policy_version(baseline) == _score_policy_version(candidate)
    if not score_policy_equal:
        warnings.append(
            "Score-policy version differs; score deltas reflect a methodology change and are not directly comparable."
        )
    resolution_is_safe = coverage_equal and rule_pack_equal

    baseline_keys = set(baseline_by_fingerprint)
    candidate_keys = set(candidate_by_fingerprint)
    new = [
        _change(
            candidate_by_fingerprint[key],
            candidate_severity=candidate_by_fingerprint[key].severity.value,
        )
        for key in sorted(candidate_keys - baseline_keys)
    ]
    missing = [
        _change(
            baseline_by_fingerprint[key],
            baseline_severity=baseline_by_fingerprint[key].severity.value,
        )
        for key in sorted(baseline_keys - candidate_keys)
    ]
    recurring: list[FindingChange] = []
    severity_changes: list[FindingChange] = []
    for key in sorted(baseline_keys & candidate_keys):
        before = baseline_by_fingerprint[key]
        after = candidate_by_fingerprint[key]
        change = _change(
            after,
            baseline_severity=before.severity.value,
            candidate_severity=after.severity.value,
        )
        recurring.append(change)
        if before.severity != after.severity:
            severity_changes.append(change)

    return ScanComparison(
        baseline_scan_id=str(baseline.scan["id"]),
        candidate_scan_id=str(candidate.scan["id"]),
        compatible=True,
        warnings=warnings,
        new_findings=new,
        resolved_findings=missing if resolution_is_safe else [],
        not_observed_findings=[] if resolution_is_safe else missing,
        recurring_findings=recurring,
        severity_changes=severity_changes,
        score_changes=_score_changes(baseline, candidate),
    )


def _score_changes(baseline: ReportDocument, candidate: ReportDocument) -> list[ScoreChange]:
    changes: list[ScoreChange] = []
    for name in sorted(set(baseline.scores) | set(candidate.scores)):
        before = baseline.scores.get(name)
        after = candidate.scores.get(name)
        delta = round(after - before, 6) if before is not None and after is not None else None
        changes.append(ScoreChange(name=name, baseline=before, candidate=after, delta=delta))
    return changes
