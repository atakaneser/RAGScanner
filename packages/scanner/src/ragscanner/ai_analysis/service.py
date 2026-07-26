"""Build bounded, redacted report context for optional model providers."""

import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from ragscanner.ai_analysis.models import AIProviderConfig, AIReportAnalysis
from ragscanner.domain.helpers import mask_secret_like_values, truncate_text
from ragscanner.reporting.models import ReportDocument

MAX_ANALYSIS_CONTEXT_CHARACTERS = 18_000
MAX_ANALYSIS_FINDING_GROUPS = 25
MAX_ANALYSIS_EVIDENCE_ROWS = 4
MAX_ANALYSIS_COVERAGE_ROWS = 20
_SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


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
    return [_safe(value, 100) for value in values[:5]]


def _evidence_snippet(rule_id: str, value: str, *, unsafe_source: bool = False) -> str:
    """Keep adversarial security payloads out of the advisory model context."""

    if rule_id.startswith("STATIC-") or unsafe_source:
        return "[omitted: untrusted security payload]"
    return _safe(value, 360)


def _encoded_characters(value: dict[str, Any]) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _affected_chunks(items: list[Any], duplicate_by_id: dict[str, Any]) -> tuple[int, Any | None]:
    group_id = items[0].metadata.get("group_id")
    duplicate_group = duplicate_by_id.get(str(group_id)) if group_id is not None else None
    if duplicate_group is not None:
        return duplicate_group.affected_chunks, duplicate_group
    return len({item.chunk_id or item.id for item in items}), None


def _compact_group(group: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        {
            "file": _safe(str(item.get("file") or "unknown"), 180),
            "page": item.get("page"),
            "lines": str(item.get("lines") or ""),
            "snippet": _safe(str(item.get("snippet") or ""), 140),
            "labels": [],
        }
        for item in group["evidence"][:2]
    ]
    return {
        **group,
        "title": _safe(str(group["title"]), 140),
        "matched_content": None,
        "impact": _safe(str(group["impact"]), 180),
        "recommendation": _safe(str(group["recommendation"]), 260),
        "evidence": evidence,
    }


def build_analysis_request(
    report: ReportDocument, *, output_language: str = "en"
) -> AnalysisRequest:
    """Return a bounded, redacted, group-aware summary for advisory interpretation."""

    duplicate_by_id = {group.id: group for group in report.duplicate_groups}
    unsafe_sources = {
        finding.source
        for finding in report.findings
        if finding.rule_id.startswith("STATIC-") and finding.source
    }
    grouped: defaultdict[str, list[Any]] = defaultdict(list)
    for finding in report.findings:
        group_id = finding.metadata.get("group_id")
        key = f"group:{group_id}" if group_id else f"rule:{finding.rule_id}"
        grouped[key].append(finding)

    coverage = [
        {
            "area": _safe(area, 160),
            "status": ("evaluated" if str(value.get("status")) == "assessed" else "not_evaluated"),
            "reason": _safe(str(value.get("reason") or ""), 300),
        }
        for area, value in sorted(report.assessment_coverage.items())[:MAX_ANALYSIS_COVERAGE_ROWS]
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
    base_context: dict[str, Any] = {
        "meta": {
            "source": _safe(str(report.scan.get("source_name") or ""), 300),
            "status": _safe(str(report.scan.get("status") or ""), 120),
            "created_at": report.generated_at.isoformat(),
        },
        "scores": scores,
        "severity_counts": severity_counts,
        "coverage": coverage,
        "limitations": [_safe(value, 400) for value in report.limitations[:8]],
    }

    prioritized = sorted(
        grouped.items(),
        key=lambda entry: (
            _SEVERITY_PRIORITY.get(entry[1][0].severity.value, 99),
            -_affected_chunks(entry[1], duplicate_by_id)[0],
            entry[0],
        ),
    )[:MAX_ANALYSIS_FINDING_GROUPS]
    summary: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    finding_ids_by_rule: defaultdict[str, list[str]] = defaultdict(list)
    for _key, items in prioritized:
        reference = items[0]
        affected_chunks, duplicate_group = _affected_chunks(items, duplicate_by_id)
        if duplicate_group is not None:
            evidence = [
                {
                    "file": _safe(member.source or "unknown", 300),
                    "page": member.page,
                    "lines": _lines(member.line_start, member.line_end),
                    "snippet": _evidence_snippet(
                        reference.rule_id,
                        member.evidence_excerpt or "",
                        unsafe_source=member.source in unsafe_sources,
                    ),
                    "labels": _labels(member.section, {}),
                }
                for member in duplicate_group.members[:MAX_ANALYSIS_EVIDENCE_ROWS]
            ]
            matched_content = (
                _safe(duplicate_group.matched_content, 240)
                if duplicate_group.matched_content
                and not any(member.source in unsafe_sources for member in duplicate_group.members)
                else None
            )
        else:
            evidence = [
                {
                    "file": _safe(item.source or "unknown", 300),
                    "page": item.page,
                    "lines": _lines(item.line_start, item.line_end),
                    "snippet": _evidence_snippet(
                        item.rule_id,
                        item.evidence_highlight or item.evidence,
                        unsafe_source=item.source in unsafe_sources,
                    ),
                    "labels": _labels(item.section, item.metadata),
                }
                for item in items[:MAX_ANALYSIS_EVIDENCE_ROWS]
            ]
            matched_content = None
        group = {
            "rule_id": _safe(reference.rule_id, 160),
            "title": _safe(reference.title, 220),
            "severity": reference.severity.value,
            "affected_chunks": affected_chunks,
            "matched_content": matched_content,
            "impact": _safe(reference.impact, 360),
            "recommendation": _safe(reference.recommendation, 480),
            "evidence": evidence,
        }
        candidate_summary = [*summary, group]
        candidate_context = {
            **base_context,
            "selection": {
                "total_finding_groups": len(grouped),
                "included_finding_groups": len(candidate_summary),
                "omitted_finding_groups": len(grouped) - len(candidate_summary),
                "method": "highest_severity_then_affected_chunks",
            },
            "findings": candidate_summary,
        }
        if _encoded_characters(candidate_context) > MAX_ANALYSIS_CONTEXT_CHARACTERS:
            group = _compact_group(group)
            candidate_summary = [*summary, group]
            candidate_context["findings"] = candidate_summary
        if _encoded_characters(candidate_context) > MAX_ANALYSIS_CONTEXT_CHARACTERS:
            break
        summary = candidate_summary
        finding_ids.update(item.id for item in items)
        finding_ids_by_rule[reference.rule_id].extend(item.id for item in items)

    context = {
        **base_context,
        "selection": {
            "total_finding_groups": len(grouped),
            "included_finding_groups": len(summary),
            "omitted_finding_groups": len(grouped) - len(summary),
            "method": "highest_severity_then_affected_chunks",
        },
        "findings": summary,
    }
    return AnalysisRequest(
        report_id=str(report.scan["id"]),
        report_language=output_language,
        finding_ids=finding_ids,
        finding_ids_by_rule=dict(finding_ids_by_rule),
        severity_counts=severity_counts,
        context=context,
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
