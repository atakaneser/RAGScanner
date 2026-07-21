"""Bounded deterministic consistency checks for repeated labelled facts."""

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ragscanner.domain import (
    DetectionType,
    Document,
    EvaluationClassification,
    Finding,
    Severity,
    SourceLocation,
)
from ragscanner.domain.helpers import mask_secret_like_values, truncate_text

_LABELLED_VALUE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?P<label>[\wÀ-\u024fİıĞğŞşÇçÖöÜü][\wÀ-\u024fİıĞğŞşÇçÖöÜü /_.()-]{2,78})"
    r"\s*[:=]\s*(?P<value>[^\n]{1,180})\s*$"
)
_SPACE = re.compile(r"\s+")
_PROCEDURAL_LABEL = re.compile(
    r"(?ix)^(?:\d+\s*[.)-]?\s*)?"
    r"(?:adım|step|aşama|stage|madde|item|bölüm|section|sayfa|page|şekil|figure|tablo|table)"
    r"(?:\s*\d+)?$"
)
_NARRATIVE_LABELS = frozenset(
    {
        "açıklama",
        "answer",
        "başlık",
        "cevap",
        "description",
        "example",
        "note",
        "not",
        "örnek",
        "question",
        "soru",
        "title",
        "uyarı",
        "warning",
    }
)


@dataclass(frozen=True, slots=True)
class _Fact:
    label: str
    value: str
    start: int
    end: int
    document: Document


class ConsistencyScanResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    facts_compared: int = Field(default=0, ge=0)
    conflicting_keys: int = Field(default=0, ge=0)


class ConsistencyScanner:
    """Find conflicting values for the same explicit label without semantic inference."""

    name = "consistency_scanner"
    version = "1.1.0"

    def scan(self, documents: list[Document]) -> ConsistencyScanResult:
        facts: dict[tuple[str, str], list[_Fact]] = defaultdict(list)
        for document in documents:
            for match in _LABELLED_VALUE.finditer(document.normalized_content):
                label = self._normalized_label(match.group("label"))
                value = self._normalize(match.group("value"))
                if label is not None and value:
                    facts[(self._source_scope(document), label)].append(
                        _Fact(
                            label=match.group("label").strip(),
                            value=match.group("value").strip(),
                            start=match.start("value"),
                            end=match.end("value"),
                            document=document,
                        )
                    )
        findings: list[Finding] = []
        conflicting_keys = 0
        for (scope, key), candidates in sorted(facts.items()):
            distinct = {self._normalize(item.value) for item in candidates}
            if len(candidates) < 2 or len(distinct) < 2:
                continue
            conflicting_keys += 1
            display_values = sorted(
                {truncate_text(mask_secret_like_values(item.value), 120) for item in candidates}
            )
            for candidate in candidates:
                findings.append(self._finding(scope, key, candidate, display_values))
        return ConsistencyScanResult(
            findings=findings,
            facts_compared=sum(len(items) for items in facts.values() if len(items) > 1),
            conflicting_keys=conflicting_keys,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return _SPACE.sub(" ", value).strip(" .;\t").casefold()

    @classmethod
    def _normalized_label(cls, value: str) -> str | None:
        label = cls._normalize(value)
        if _PROCEDURAL_LABEL.fullmatch(label) or label in _NARRATIVE_LABELS:
            return None
        return label

    @staticmethod
    def _source_scope(document: Document) -> str:
        source = document.source
        identity = (
            source.source_path or f"{source.source_type}:{source.source_name}:{source.source_id}"
        )
        return _SPACE.sub(" ", identity).strip().casefold()

    def _finding(self, scope: str, key: str, fact: _Fact, values: list[str]) -> Finding:
        source = self._source_location(fact)
        safe_value = truncate_text(mask_secret_like_values(fact.value), 180)
        evidence = f"{fact.label}: {safe_value}"
        fingerprint = hashlib.sha256(
            (
                f"consistency:v2:{scope}:{key}:{source.source_id}:{fact.document.id}:"
                f"{fact.start}:{'|'.join(values)}"
            ).encode()
        ).hexdigest()
        return Finding(
            id=fingerprint,
            fingerprint=fingerprint,
            category="consistency_conflict",
            scanner=self.name,
            rule_id="QUALITY-CONSISTENCY-CONFLICT",
            rule_version=self.version,
            title="Conflicting labelled information",
            description="The same labelled fact has multiple distinct values in the assessed content.",
            severity=Severity.HIGH,
            confidence=0.92,
            detection_type=DetectionType.DETERMINISTIC,
            classification=EvaluationClassification.CONFIRMED,
            source=source,
            document_id=fact.document.id,
            evidence=evidence,
            impact="Retrieval may return mutually inconsistent guidance without warning the user.",
            recommendation=(
                "Choose and document one authoritative value, mark superseded guidance, and "
                "re-index the affected sources after review."
            ),
            first_seen=fact.document.ingested_at,
            last_seen=fact.document.ingested_at,
            metadata={
                "label": truncate_text(fact.label, 80),
                "conflicting_values": values[:8],
                "normalized_start": fact.start,
                "normalized_end": fact.end,
                "matched_text": safe_value,
                "automatic_modification": False,
            },
        )

    @staticmethod
    def _source_location(fact: _Fact) -> SourceLocation:
        line = fact.document.normalized_content.count("\n", 0, fact.start) + 1
        page = fact.document.source.page_number
        pages = fact.document.metadata.get("pages")
        if isinstance(pages, list):
            for candidate in pages:
                if not isinstance(candidate, dict):
                    continue
                start = candidate.get("start_offset")
                end = candidate.get("end_offset")
                number = candidate.get("page_number")
                if isinstance(start, int) and isinstance(end, int) and start <= fact.start <= end:
                    page = number if isinstance(number, int) else page
                    break
        return fact.document.source.model_copy(
            update={"page_number": page, "line_start": line, "line_end": line}
        )
