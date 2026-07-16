"""Build bounded, redacted report context for optional model providers."""

from typing import Any

from pydantic import BaseModel, Field

from ragscanner.domain.helpers import mask_secret_like_values, truncate_text
from ragscanner.reporting.models import ReportDocument


class AnalysisRequest(BaseModel):
    report_id: str
    context: dict[str, Any]
    finding_ids: set[str] = Field(default_factory=set)


def _safe(value: str, limit: int = 700) -> str:
    return truncate_text(mask_secret_like_values(value), limit)


def build_analysis_request(report: ReportDocument) -> AnalysisRequest:
    """Return a no-evidence summary so providers never receive raw document content."""

    findings = report.findings[:25]
    summary = [
        {
            "id": item.id,
            "severity": item.severity.value,
            "category": _safe(item.category, 120),
            "title": _safe(item.title, 300),
            "impact": _safe(item.impact),
            "recommendation": _safe(item.recommendation),
        }
        for item in findings
    ]
    return AnalysisRequest(
        report_id=str(report.scan["id"]),
        finding_ids={item.id for item in findings},
        context={
            "report_id": str(report.scan["id"]),
            "scores": report.scores,
            "severity_summary": report.severity_summary,
            "processing": report.processing.model_dump(mode="json"),
            "assessment_coverage": report.assessment_coverage,
            "findings": summary,
            "notes": [
                "This is a bounded summary, not source material.",
                "Do not infer facts outside these findings.",
                "Return advisory actions only; do not present a security guarantee.",
            ],
        },
    )
