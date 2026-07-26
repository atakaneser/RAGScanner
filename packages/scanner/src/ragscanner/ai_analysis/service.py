"""Build bounded, redacted report context for optional model providers."""

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from ragscanner.ai_analysis.models import AIProviderConfig, AIReportAnalysis
from ragscanner.domain.helpers import mask_secret_like_values, truncate_text
from ragscanner.reporting.models import ReportDocument


class AnalysisRequest(BaseModel):
    report_id: str
    report_language: str = "en"
    context: dict[str, Any]
    finding_ids: set[str] = Field(default_factory=set)
    finding_ids_by_rule: dict[str, list[str]] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)


def _safe(value: str, limit: int = 700) -> str:
    return truncate_text(mask_secret_like_values(value), limit)


def _lines(line_start: int | None, line_end: int | None) -> str:
    if line_start is None:
        return ""
    if line_end is None or line_end == line_start:
        return str(line_start)
    return f"{line_start}-{line_end}"


def _labels(section: str | None, metadata: dict[str, Any]) -> list[str]:
    values = [section] if section else []
    supplied = metadata.get("labels")
    if isinstance(supplied, list):
        values.extend(value for value in supplied if isinstance(value, str))
    return [_safe(value, 160) for value in values[:10]]


def build_analysis_request(
    report: ReportDocument, *, output_language: str = "en"
) -> AnalysisRequest:
    """Return a bounded, redacted, group-aware summary for advisory interpretation."""

    duplicate_by_id = {group.id: group for group in report.duplicate_groups}
    grouped: defaultdict[str, list[Any]] = defaultdict(list)
    for finding in report.findings:
        group_id = finding.metadata.get("group_id")
        key = f"group:{group_id}" if group_id else f"rule:{finding.rule_id}"
        grouped[key].append(finding)

    summary: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    finding_ids_by_rule: defaultdict[str, list[str]] = defaultdict(list)
    for key in sorted(grouped)[:25]:
        items = grouped[key]
        reference = items[0]
        finding_ids.update(item.id for item in items)
        finding_ids_by_rule[reference.rule_id].extend(item.id for item in items)
        group_id = reference.metadata.get("group_id")
        duplicate_group = duplicate_by_id.get(str(group_id)) if group_id is not None else None
        if duplicate_group is not None:
            evidence = [
                {
                    "file": _safe(member.source or "unknown", 500),
                    "page": member.page,
                    "lines": _lines(member.line_start, member.line_end),
                    "snippet": _safe(member.evidence_excerpt or "", 700),
                    "labels": _labels(member.section, {}),
                }
                for member in duplicate_group.members[:10]
            ]
            affected_chunks = duplicate_group.affected_chunks
            matched_content = (
                _safe(duplicate_group.matched_content, 700)
                if duplicate_group.matched_content
                else None
            )
        else:
            evidence = [
                {
                    "file": _safe(item.source or "unknown", 500),
                    "page": item.page,
                    "lines": _lines(item.line_start, item.line_end),
                    "snippet": _safe(item.evidence_highlight or item.evidence, 700),
                    "labels": _labels(item.section, item.metadata),
                }
                for item in items[:10]
            ]
            affected_chunks = len({item.chunk_id or item.id for item in items})
            matched_content = None
        summary.append(
            {
                "rule_id": _safe(reference.rule_id, 240),
                "title": _safe(reference.title, 300),
                "severity": reference.severity.value,
                "affected_chunks": affected_chunks,
                "matched_content": matched_content,
                "impact": _safe(reference.impact),
                "recommendation": _safe(reference.recommendation),
                "evidence": evidence,
            }
        )

    coverage = [
        {
            "area": _safe(area, 240),
            "status": ("evaluated" if str(value.get("status")) == "assessed" else "not_evaluated"),
            "reason": _safe(str(value.get("reason") or ""), 700),
        }
        for area, value in sorted(report.assessment_coverage.items())
    ]
    scores = {
        "overall": report.scores.get("overall"),
        "security": report.scores.get("security"),
        "content_quality": report.scores.get("knowledge_quality"),
        "efficiency": report.scores.get("efficiency"),
    }
    severity_counts = {
        severity: int(report.severity_summary.get(severity, 0))
        for severity in ("critical", "high", "medium", "low", "info")
    }
    return AnalysisRequest(
        report_id=str(report.scan["id"]),
        report_language=output_language,
        finding_ids=finding_ids,
        finding_ids_by_rule=dict(finding_ids_by_rule),
        severity_counts=severity_counts,
        context={
            "meta": {
                "source": _safe(str(report.scan.get("source_name") or ""), 500),
                "status": _safe(str(report.scan.get("status") or ""), 120),
                "created_at": report.generated_at.isoformat(),
            },
            "scores": scores,
            "severity_counts": severity_counts,
            "findings": summary,
            "coverage": coverage,
            "limitations": [_safe(value, 700) for value in report.limitations[:20]],
        },
    )


async def enrich_report(
    report: ReportDocument,
    config: AIProviderConfig,
    *,
    provider_factory: Callable[[AIProviderConfig], Any],
) -> ReportDocument:
    """Add advisory analysis without changing deterministic findings or scores."""

    if not config.enabled:
        return report
    provider = provider_factory(config)
    result: Awaitable[AIReportAnalysis] = provider.analyze(
        build_analysis_request(report, output_language=config.output_language)
    )
    analysis = await result
    return report.model_copy(update={"ai_analysis": analysis, "ai_analysis_error": None})
