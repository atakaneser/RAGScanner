"""Deterministic report view-model building and report-boundary redaction."""

import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ragscanner.domain import EvaluationClassification, ExecutionStatus, Severity
from ragscanner.domain.helpers import REDACTED, mask_secret_like_values, truncate_text
from ragscanner.reporting.models import (
    ReportDocument,
    ReportDuplicateGroup,
    ReportDuplicateMember,
    ReportFilter,
    ReportFinding,
    ReportIngestionIssue,
    ReportInput,
    ReportLimits,
    ReportProcessingSummary,
)

_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}
_CLASSIFICATION_RANK = {
    EvaluationClassification.CONFIRMED: 0,
    EvaluationClassification.PROBABLE: 1,
    EvaluationClassification.AMBIGUOUS: 2,
    EvaluationClassification.INCONCLUSIVE: 3,
    EvaluationClassification.NOT_DETECTED: 4,
    None: 5,
}
_SENSITIVE_KEY = re.compile(
    r"(?i)^(?:authorization|api[_-]?key|(?:access[_-]?)?token|secret|password|credential|cookie|private[_-]?key)$"
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.DOTALL,
)
_CONNECTION = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+")


def _redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if parts.scheme.casefold() in {"javascript", "data", "file", "vbscript"}:
        return "[UNSAFE-URL-SCHEME]"
    if not parts.scheme or not parts.netloc:
        return value
    try:
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return value
    if port:
        host = f"{host}:{port}"
    query = urlencode(
        [
            (key, REDACTED if _SENSITIVE_KEY.search(key) else item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, host, parts.path, query, parts.fragment))


def _safe_string(value: str, limit: int) -> str:
    value = _PRIVATE_KEY.sub(REDACTED, value)
    value = _CONNECTION.sub(REDACTED, value)
    value = mask_secret_like_values(value)
    value = _redact_url(value)
    return truncate_text(value, limit)


def _safe_value(value: Any, limits: ReportLimits, *, key: str = "") -> Any:
    if _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, str):
        return _safe_string(value, limits.maximum_string_length)
    if isinstance(value, dict):
        return {
            str(item_key): _safe_value(item, limits, key=str(item_key))
            for item_key, item in sorted(value.items(), key=lambda pair: str(pair[0]))[
                : limits.maximum_metadata_fields
            ]
        }
    if isinstance(value, list | tuple | set):
        return [
            _safe_value(item, limits, key=key)
            for item in list(value)[: limits.maximum_metadata_fields]
        ]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return _safe_string(str(value), limits.maximum_string_length)


class ReportBuilder:
    """Build a redacted deterministic report document without mutating scan results."""

    def __init__(
        self,
        *,
        filters: ReportFilter | None = None,
        limits: ReportLimits | None = None,
        show_absolute_paths: bool = False,
    ) -> None:
        self.filters = filters or ReportFilter()
        self.limits = limits or ReportLimits()
        self.show_absolute_paths = show_absolute_paths

    def build(self, source: ReportInput) -> ReportDocument:
        notices: list[str] = []
        selected = [item for item in source.findings if self._matches(item)]
        selected.sort(key=self._finding_key)
        if len(selected) > self.limits.maximum_findings:
            notices.append(
                f"Findings limited to {self.limits.maximum_findings} of {len(selected)}."
            )
            selected = selected[: self.limits.maximum_findings]
        findings = [self._finding(item) for item in selected]
        groups = [
            self._group(item, notices)
            for item in sorted(source.duplicate_groups, key=lambda g: (g.category, g.id))
        ]
        warnings = self._bounded_messages(
            source.scan.warnings + source.warnings, notices, "Warnings"
        )
        errors = self._bounded_messages(source.scan.errors + source.errors, notices, "Errors")
        skipped = self._bounded_messages(source.skipped_checks, notices, "Skipped checks")
        score_values: dict[str, float | None] = (
            source.scores.model_dump(mode="json")
            if source.scores is not None
            else {
                name: None
                for name in (
                    "overall",
                    "knowledge_quality",
                    "retrieval_quality",
                    "answer_reliability",
                    "security",
                    "freshness",
                    "efficiency",
                    "rag_rot",
                )
            }
        )
        severity = {item.value: 0 for item in Severity}
        classifications = {item.value: 0 for item in EvaluationClassification}
        for finding in findings:
            severity[finding.severity.value] += 1
            if finding.classification is not None:
                classifications[finding.classification.value] += 1
        scan = source.scan
        duration = None
        if scan.started_at and scan.completed_at:
            duration = (scan.completed_at - scan.started_at).total_seconds()
        active = (
            self._active_summary(source) if scan.scan_type.value in {"active", "combined"} else None
        )
        duplicate_summary: dict[str, int | float] = {
            "exact_document_groups": sum(g.category == "exact_duplicate_document" for g in groups),
            "exact_chunk_groups": sum(
                g.category in {"exact_duplicate_chunk", "repeated_chunk_within_document"}
                for g in groups
            ),
            "near_duplicate_groups": sum(g.category.startswith("near_duplicate") for g in groups),
            "estimated_redundant_characters": sum(g.estimated_redundant_characters for g in groups),
            "estimated_redundant_tokens": sum(g.estimated_redundant_tokens for g in groups),
        }
        return ReportDocument(
            generated_at=source.generated_at,
            scan={
                "id": scan.id,
                "type": scan.scan_type.value,
                "status": scan.status.value,
                "source_name": _safe_string(
                    scan.source_name or "", self.limits.maximum_string_length
                )
                or None,
                "target_name": _safe_string(
                    source.target_name or scan.target_id or "", self.limits.maximum_string_length
                )
                or None,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "duration_seconds": duration,
                "scanner_version": scan.scanner_version,
                "rule_pack_version": scan.rule_pack_version,
                "analysis_mode": scan.mode.value,
                "safety_mode": scan.safety_mode.value,
                "privacy_mode": scan.privacy_mode.value,
                "model_provider": _safe_string(scan.model_provider or "", 256) or None,
                "model_name": _safe_string(scan.model_name or "", 256) or None,
            },
            processing=ReportProcessingSummary(
                files_discovered=scan.files_discovered,
                files_scanned=scan.files_scanned,
                files_skipped=scan.files_skipped,
                documents_parsed=source.documents_parsed,
                chunks_scanned=scan.chunks_scanned,
                active_requests_planned=scan.requests_planned,
                active_requests_sent=scan.requests_sent,
                active_requests_failed=scan.requests_failed,
                rules_evaluated=max(len(source.rules_evaluated), source.rules_evaluated_count),
                rules_skipped=max(len(source.rules_skipped), source.rules_skipped_count),
                warnings=len(warnings),
                errors=len(errors),
            ),
            scores=score_values,
            score_policy_details=source.score_policy_details,
            rag_configuration_advice=source.rag_configuration_advice,
            severity_summary=severity,
            classification_summary=classifications,
            findings=findings,
            duplicate_groups=groups,
            duplicate_summary=duplicate_summary,
            chunk_quality=_safe_value(source.chunk_quality_statistics.model_dump(), self.limits)
            if source.chunk_quality_statistics
            else None,
            active_security=active,
            warnings=warnings,
            skipped_checks=skipped,
            errors=errors,
            configuration=_safe_value(source.configuration_summary, self.limits),
            methodology=[
                _safe_string(item, self.limits.maximum_string_length) for item in source.methodology
            ],
            limitations=[
                _safe_string(item, self.limits.maximum_string_length) for item in source.limitations
            ],
            filters_active=self.filters.is_active(),
            filter_summary=_safe_value(self.filters.model_dump(mode="json"), self.limits),
            truncation_notices=notices,
            metadata=_safe_value(source.metadata, self.limits),
            knowledge_base_mode=_safe_string(source.knowledge_base_mode, 128),
            source_count=source.source_count,
            assessment_coverage=_safe_value(source.assessment_coverage, self.limits),
            ingestion_issues=[self._ingestion_issue(item) for item in source.ingestion_issues],
        )

    def _ingestion_issue(self, item: dict[str, Any]) -> ReportIngestionIssue:
        raw_path = str(item.get("path") or "unknown")
        path = raw_path if self.show_absolute_paths else Path(raw_path).name
        remediation = item.get("remediation")
        return ReportIngestionIssue(
            path=_safe_string(path, 1_024),
            stage=_safe_string(str(item.get("stage") or "unknown"), 128),
            code=_safe_string(str(item.get("code") or "unknown"), 256),
            message=_safe_string(str(item.get("message") or "No details recorded."), 2_048),
            remediation=(
                _safe_string(str(remediation), 2_048) if remediation is not None else None
            ),
            fatal=bool(item.get("fatal", False)),
        )

    def _matches(self, finding: Any) -> bool:
        if (
            self.filters.minimum_severity
            and _SEVERITY_RANK[finding.severity] < _SEVERITY_RANK[self.filters.minimum_severity]
        ):
            return False
        if not self.filters.include_informational and finding.severity is Severity.INFO:
            return False
        return not (
            (self.filters.categories and finding.category not in self.filters.categories)
            or (
                self.filters.classifications
                and finding.classification not in self.filters.classifications
            )
            or (self.filters.document_id and finding.document_id != self.filters.document_id)
            or (self.filters.target_id and finding.target_id != self.filters.target_id)
            or (self.filters.rule_ids and finding.rule_id not in self.filters.rule_ids)
        )

    @staticmethod
    def _finding_key(item: Any) -> tuple[Any, ...]:
        source = item.source.source_path if item.source and item.source.source_path else ""
        return (
            -_SEVERITY_RANK[item.severity],
            _CLASSIFICATION_RANK[item.classification],
            -item.confidence,
            item.category,
            source,
            item.rule_id,
            item.fingerprint,
        )

    def _finding(self, item: Any) -> ReportFinding:
        path = item.source.source_path if item.source else None
        if path and not self.show_absolute_paths:
            path = Path(path).name
        return ReportFinding(
            id=_safe_string(item.id, 512),
            title=_safe_string(item.title, 1_024),
            category=_safe_string(item.category, 256),
            severity=item.severity,
            confidence=item.confidence,
            classification=item.classification,
            detection_type=item.detection_type.value,
            scanner=_safe_string(item.scanner, 256),
            rule_id=_safe_string(item.rule_id, 256),
            rule_version=_safe_string(item.rule_version, 64),
            source=_safe_string(path, 1_024) if path else None,
            document_id=item.document_id,
            page=item.source.page_number if item.source else None,
            line_start=item.source.line_start if item.source else None,
            line_end=item.source.line_end if item.source else None,
            chunk_id=item.chunk_id,
            target_id=item.target_id,
            test_case_id=item.test_case_id,
            execution_id=item.execution_id,
            evidence=_safe_string(item.evidence, self.limits.maximum_evidence_length),
            evidence_highlight=(
                _safe_string(str(item.metadata.get("matched_text")), 512)
                if item.metadata.get("matched_text")
                else None
            ),
            impact=_safe_string(item.impact, self.limits.maximum_string_length),
            recommendation=_safe_string(item.recommendation, self.limits.maximum_string_length),
            references=[_safe_string(value, 1_024) for value in item.references[:50]],
            first_seen=item.first_seen,
            last_seen=item.last_seen,
            fingerprint=item.fingerprint,
            metadata=_safe_value(item.metadata, self.limits),
        )

    def _group(self, item: Any, notices: list[str]) -> ReportDuplicateGroup:
        selected_members = list(item.members)
        truncated = len(selected_members) > self.limits.maximum_duplicate_group_members
        if truncated:
            notices.append(f"Duplicate group {item.id} members were limited.")
            selected_members = selected_members[: self.limits.maximum_duplicate_group_members]

        def member_source(member: Any) -> str | None:
            value = member.source.source_path or member.source.source_name
            if value and not self.show_absolute_paths:
                value = Path(value).name
            return _safe_string(value, 1_024) if value else None

        members = [
            ReportDuplicateMember(
                item_type=member.item_type.value,
                item_id=member.item_id,
                document_id=member.document_id,
                chunk_id=member.chunk_id,
                source=member_source(member),
                page=member.source.page_number,
                section=_safe_string(member.source.section or "", self.limits.maximum_string_length)
                or None,
                line_start=member.source.line_start,
                line_end=member.source.line_end,
                character_count=member.character_count,
                token_count=member.token_count,
                evidence_excerpt=(
                    _safe_string(
                        member.evidence_excerpt,
                        self.limits.maximum_evidence_length,
                    )
                    if member.evidence_excerpt
                    else None
                ),
                canonical=member.item_id == item.canonical_item_id,
            )
            for member in selected_members
        ]
        related = [
            member.item_id for member in item.members if member.item_id != item.canonical_item_id
        ][: self.limits.maximum_duplicate_group_members]
        return ReportDuplicateGroup(
            id=item.id,
            category=item.category,
            canonical_item_id=item.canonical_item_id,
            related_item_ids=related,
            similarity=item.similarity,
            estimated_redundant_characters=item.estimated_redundant_characters,
            estimated_redundant_tokens=item.estimated_redundant_tokens,
            members_truncated=truncated,
            members=members,
            shared_phrases=[
                _safe_string(value, 200)
                for value in item.metadata.get("shared_phrases", [])[:10]
                if isinstance(value, str)
            ],
        )

    def _bounded_messages(self, values: list[str], notices: list[str], label: str) -> list[str]:
        safe = sorted({_safe_string(value, self.limits.maximum_string_length) for value in values})
        if len(safe) > self.limits.maximum_warnings:
            notices.append(f"{label} limited to {self.limits.maximum_warnings} of {len(safe)}.")
            safe = safe[: self.limits.maximum_warnings]
        return safe

    def _active_summary(self, source: ReportInput) -> dict[str, Any]:
        statuses = {status.value: 0 for status in ExecutionStatus}
        for execution in source.executions:
            statuses[execution.status.value] += 1
        controls = sum(bool(item.metadata.get("is_control")) for item in source.executions)
        return {
            "tests_selected": len({item.test_case_id for item in source.executions}),
            "tests_skipped": len(source.rules_skipped),
            "controls_executed": controls,
            "attack_payloads_executed": max(0, len(source.executions) - controls),
            "transport_failures": statuses[ExecutionStatus.FAILED.value],
            "target_capabilities": sorted(
                _safe_string(item, 256) for item in source.target_capabilities
            ),
            "authorization_scope": _safe_string(
                source.authorization_summary or "Authorized scope recorded; actor hidden.", 512
            ),
            "safety_mode": source.scan.safety_mode.value,
            "request_budget_usage": {
                "sent": source.scan.requests_sent,
                "planned": source.scan.requests_planned,
            },
            "execution_statuses": statuses,
        }
