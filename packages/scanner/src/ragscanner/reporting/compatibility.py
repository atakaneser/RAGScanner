"""Read-time compatibility for reports produced by superseded scanners."""

from collections.abc import Sequence

from ragscanner.reporting.models import ReportDocument, ReportFinding

_REMOVED_CONSISTENCY_SCANNER = "consistency_scanner"
_REMOVED_CONSISTENCY_CATEGORY = "consistency_conflict"


def without_removed_consistency(report: ReportDocument) -> ReportDocument:
    """Hide retired contradiction results and recompute affected historical scores."""
    removed_findings = [
        finding
        for finding in report.findings
        if finding.scanner == _REMOVED_CONSISTENCY_SCANNER
        or finding.category == _REMOVED_CONSISTENCY_CATEGORY
    ]
    has_removed_score = "consistency" in report.scores
    has_removed_coverage = "consistency" in report.assessment_coverage
    if not removed_findings and not has_removed_score and not has_removed_coverage:
        return report

    findings = [finding for finding in report.findings if finding not in removed_findings]
    scores = {name: value for name, value in report.scores.items() if name != "consistency"}
    scores["overall"] = _recomputed_overall(report, scores, findings)
    coverage = {
        name: value for name, value in report.assessment_coverage.items() if name != "consistency"
    }
    if "version_conflict" in coverage:
        coverage["version_conflict"] = {
            "status": "not_assessed",
            "reason": "Semantic contradiction detection is not currently assessed.",
        }

    severity_summary = dict(report.severity_summary)
    classification_summary = dict(report.classification_summary)
    for finding in removed_findings:
        severity = getattr(finding.severity, "value", finding.severity)
        severity_summary[severity] = max(0, severity_summary.get(severity, 0) - 1)
        if finding.classification is not None:
            classification = getattr(finding.classification, "value", finding.classification)
            classification_summary[classification] = max(
                0, classification_summary.get(classification, 0) - 1
            )

    return report.model_copy(
        update={
            "scores": scores,
            "findings": findings,
            "severity_summary": severity_summary,
            "classification_summary": classification_summary,
            "assessment_coverage": coverage,
            # A historical narrative may discuss findings that were removed from display.
            "ai_analysis": None if removed_findings else report.ai_analysis,
        }
    )


def _recomputed_overall(
    report: ReportDocument,
    scores: dict[str, float | None],
    findings: Sequence[ReportFinding],
) -> float | None:
    dimensions = {
        "security": (
            scores.get("security"),
            0.35
            + min(
                0.15,
                sum(
                    1
                    for finding in findings
                    if getattr(finding, "scanner", None) == "static_security_scanner"
                )
                / max(1, report.processing.documents_parsed)
                * 0.03,
            ),
        ),
        "knowledge_quality": (scores.get("knowledge_quality"), 0.20),
        "efficiency": (scores.get("efficiency"), 0.15),
    }
    assessed = [(value, weight) for value, weight in dimensions.values() if value is not None]
    if not assessed:
        return None
    return sum(value * weight for value, weight in assessed) / sum(
        weight for _value, weight in assessed
    )
