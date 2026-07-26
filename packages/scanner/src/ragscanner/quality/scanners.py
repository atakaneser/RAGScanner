"""Offline exact/near duplicate and chunk-quality scanners."""

import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from ragscanner.domain import (
    Chunk,
    DetectionType,
    Document,
    EvaluationClassification,
    Finding,
    Severity,
    SourceLocation,
)
from ragscanner.domain.helpers import document_content_hash, mask_secret_like_values
from ragscanner.normalization import AnnotationType, NormalizationResult
from ragscanner.quality.models import (
    ChunkQualityConfig,
    ChunkQualityResult,
    ChunkQualityScore,
    ChunkQualityStatistics,
    DuplicateGroup,
    DuplicateItemType,
    DuplicateMember,
    DuplicateScanConfig,
    DuplicateScanResult,
    DuplicateStatistics,
    NearDuplicateConfig,
    QualityWarning,
)

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_WORD = re.compile(r"\w+", re.UNICODE)
_PAGE_NUMBER = re.compile(r"(?i)^\s*(?:page|sayfa)?\s*[-–—]?\s*\d+(?:\s*/\s*\d+)?\s*[-–—]?\s*$")
_CONTROL_MARKER = re.compile(r"<(?:NUL|ZWSP|ZWNJ|BIDI:[A-Z]+|CONTROL:U\+[0-9A-F]+|REPLACEMENT)>")
_FRONT_MATTER_KEY = re.compile(
    r"(?im)^\s*(?:title|classification|audience|last_reviewed|related_documents|"
    r"content_style|version|owner|tags?)\s*:"
)
_GENERATED_CHUNK_MARKER = "generated_by_ragscanner"
_SENTENCE_BOUNDARY_ENDINGS = (".", "!", "?", ":", ";", "。", "！", "？", "：", "；", "```")


@dataclass(frozen=True, slots=True)
class _Item:
    item_type: DuplicateItemType
    item_id: str
    document_id: str
    chunk_id: str | None
    text: str
    source: SourceLocation
    token_count: int
    observed_at: Any


def _stable_hash(namespace: str, value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(f"{namespace}:{payload}".encode()).hexdigest()


def _safe_evidence(value: str, limit: int) -> str:
    return mask_secret_like_values(value[:limit])[:limit]


def _is_generated_chunk(chunk: Chunk) -> bool:
    return chunk.metadata.get(_GENERATED_CHUNK_MARKER) is True


def _is_generated_heading_only_chunk(chunk: Chunk) -> bool:
    if not _is_generated_chunk(chunk) or not chunk.headings:
        return False
    content = " ".join(chunk.normalized_content.split())
    return content in {" ".join(heading.split()) for heading in chunk.headings}


def _forced_split_signature(chunk: Chunk) -> tuple[bool, bool, bool]:
    return (
        chunk.metadata.get("table_present") is True,
        chunk.metadata.get("code_block_present") is True,
        chunk.metadata.get("list_present") is True,
    )


def _finding(
    *,
    scanner: str,
    version: str,
    rule_id: str,
    category: str,
    title: str,
    description: str,
    severity: Severity,
    confidence: float,
    classification: EvaluationClassification,
    source: SourceLocation,
    document_id: str,
    chunk_id: str | None,
    evidence: str,
    impact: str,
    recommendation: str,
    metadata: dict[str, Any],
    observed_at: Any,
) -> Finding:
    fingerprint = _stable_hash(
        "quality-finding:v1",
        {
            "rule": rule_id,
            "version": version,
            "document": document_id,
            "chunk": chunk_id,
            "source": source.source_path,
            "metadata": metadata,
        },
    )
    return Finding(
        id=fingerprint,
        fingerprint=fingerprint,
        category=category,
        scanner=scanner,
        rule_id=rule_id,
        rule_version=version,
        title=title,
        description=description,
        severity=severity,
        confidence=confidence,
        detection_type=DetectionType.DETERMINISTIC
        if confidence >= 0.95
        else DetectionType.HEURISTIC,
        classification=classification,
        source=source,
        document_id=document_id,
        chunk_id=chunk_id,
        evidence=evidence,
        impact=impact,
        recommendation=recommendation,
        first_seen=observed_at,
        last_seen=observed_at,
        metadata=metadata,
    )


class ExactDuplicateScanner:
    name = "exact_duplicate_scanner"
    version = "1.3.0"

    def __init__(
        self,
        config: DuplicateScanConfig | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.config = config or DuplicateScanConfig()
        self._monotonic = monotonic_clock or monotonic

    def scan(
        self,
        documents: list[Document],
        normalized: dict[str, NormalizationResult],
        chunks: list[Chunk],
    ) -> DuplicateScanResult:
        started = self._monotonic()
        warnings: list[QualityWarning] = []
        skipped: list[str] = []
        docs = sorted(documents, key=lambda item: item.id)
        chunk_values = sorted(chunks, key=lambda item: (item.document_id, item.index, item.id))
        if len(docs) > self.config.maximum_documents:
            skipped.extend(item.id for item in docs[self.config.maximum_documents :])
            docs = docs[: self.config.maximum_documents]
            warnings.append(
                QualityWarning(
                    code="maximum_documents_reached", message="Document input was bounded."
                )
            )
        if len(chunk_values) > self.config.maximum_chunks:
            skipped.extend(item.id for item in chunk_values[self.config.maximum_chunks :])
            chunk_values = chunk_values[: self.config.maximum_chunks]
            warnings.append(
                QualityWarning(code="maximum_chunks_reached", message="Chunk input was bounded.")
            )
        items = self._items(docs, normalized, chunk_values, skipped)
        buckets: defaultdict[tuple[DuplicateItemType, str], list[_Item]] = defaultdict(list)
        for item in items:
            if item.text.strip():
                buckets[(item.item_type, document_content_hash(item.text))].append(item)
        groups: list[DuplicateGroup] = []
        for (_, digest), members in sorted(
            buckets.items(), key=lambda value: (value[0][0].value, value[0][1])
        ):
            if len(members) < 2:
                continue
            members = sorted(members, key=self._canonical_key)
            category = self._category(members)
            group = self._group(category, digest, members, 1.0)
            groups.append(group)
            if len(groups) >= self.config.maximum_groups:
                warnings.append(
                    QualityWarning(
                        code="maximum_groups_reached", message="Duplicate groups were bounded."
                    )
                )
                break
            if self._monotonic() - started >= self.config.maximum_processing_seconds:
                warnings.append(
                    QualityWarning(
                        code="processing_time_limit_reached",
                        message="Duplicate scan reached its cooperative time limit.",
                    )
                )
                break
        findings = [
            self._group_finding(group, items) for group in groups[: self.config.maximum_findings]
        ]
        if len(groups) > self.config.maximum_findings:
            warnings.append(
                QualityWarning(
                    code="maximum_findings_reached", message="Duplicate findings were bounded."
                )
            )
        return self._result(docs, chunk_values, groups, findings, warnings, skipped, 0)

    def _items(
        self,
        documents: list[Document],
        normalized: dict[str, NormalizationResult],
        chunks: list[Chunk],
        skipped: list[str],
    ) -> list[_Item]:
        result: list[_Item] = []
        by_id = {document.id: document for document in documents}
        for document in documents:
            value = normalized.get(document.id)
            if value is None or value.document_id != document.id:
                skipped.append(document.id)
                continue
            result.append(
                _Item(
                    DuplicateItemType.DOCUMENT,
                    document.id,
                    document.id,
                    None,
                    value.normalized_content,
                    document.source,
                    len(_TOKEN.findall(value.normalized_content)),
                    document.ingested_at,
                )
            )
        for chunk in chunks:
            associated_document = by_id.get(chunk.document_id)
            if associated_document is None:
                skipped.append(chunk.id)
                continue
            normalized_document = normalized.get(chunk.document_id)
            if _is_generated_heading_only_chunk(chunk) or (
                normalized_document is not None
                and chunk.normalized_content == normalized_document.normalized_content
            ):
                continue
            if self._is_non_content_chunk(chunk.normalized_content):
                continue
            if (
                len(chunk.normalized_content.strip())
                < self.config.minimum_duplicate_chunk_characters
                or chunk.token_count < self.config.minimum_duplicate_chunk_tokens
            ):
                continue
            result.append(
                _Item(
                    DuplicateItemType.CHUNK,
                    chunk.id,
                    chunk.document_id,
                    chunk.id,
                    chunk.normalized_content,
                    chunk.source,
                    chunk.token_count,
                    associated_document.ingested_at,
                )
            )
        return result

    @staticmethod
    def _is_non_content_chunk(value: str) -> bool:
        stripped = value.strip()
        if not stripped or not any(character.isalnum() for character in stripped):
            return True
        return len(_FRONT_MATTER_KEY.findall(stripped)) >= 3

    @staticmethod
    def _canonical_key(item: _Item) -> tuple[str, str]:
        return item.source.source_path or "", item.item_id

    @staticmethod
    def _category(members: list[_Item]) -> str:
        if members[0].item_type is DuplicateItemType.DOCUMENT:
            return "exact_duplicate_document"
        if len({member.document_id for member in members}) == 1:
            return "repeated_chunk_within_document"
        return "exact_duplicate_chunk"

    def _group(
        self, category: str, signature: str, members: list[_Item], similarity: float
    ) -> DuplicateGroup:
        redundant = members[1:]
        group_id = _stable_hash(
            "duplicate-group:v1",
            {
                "category": category,
                "signature": signature,
                "members": [member.item_id for member in members],
            },
        )
        return DuplicateGroup(
            id=group_id,
            category=category,
            canonical_item_id=members[0].item_id,
            members=[
                DuplicateMember(
                    item_type=member.item_type,
                    item_id=member.item_id,
                    document_id=member.document_id,
                    chunk_id=member.chunk_id,
                    source=member.source,
                    normalized_hash=document_content_hash(member.text),
                    character_count=len(member.text),
                    token_count=member.token_count,
                    evidence_excerpt=_safe_evidence(
                        member.text, self.config.maximum_evidence_length
                    ),
                )
                for member in members
            ],
            similarity=similarity,
            estimated_redundant_characters=sum(len(member.text) for member in redundant),
            estimated_redundant_tokens=sum(member.token_count for member in redundant),
            metadata={"automatic_deletion_recommended": False},
        )

    def _group_finding(self, group: DuplicateGroup, items: list[_Item]) -> Finding:
        item = next(value for value in items if value.item_id == group.canonical_item_id)
        related = [
            member.item_id for member in group.members if member.item_id != group.canonical_item_id
        ]
        return _finding(
            scanner=self.name,
            version=self.version,
            rule_id=f"QUALITY-{group.category.upper().replace('_', '-')}",
            category=group.category,
            title="Exact normalized-content duplicate group",
            description="Multiple items have identical normalized content.",
            severity=Severity.MEDIUM,
            confidence=1.0,
            classification=EvaluationClassification.CONFIRMED,
            source=item.source,
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            evidence=_safe_evidence(item.text, self.config.maximum_evidence_length),
            impact="Redundant indexed content can waste storage and bias retrieval.",
            recommendation="Review the group and keep one canonical item; do not delete automatically.",
            metadata={
                "group_id": group.id,
                "canonical_item_id": group.canonical_item_id,
                "related_item_ids": related,
                "similarity": 1.0,
                "estimated_redundant_tokens": group.estimated_redundant_tokens,
            },
            observed_at=item.observed_at,
        )

    def _result(
        self,
        docs: list[Document],
        chunks: list[Chunk],
        groups: list[DuplicateGroup],
        findings: list[Finding],
        warnings: list[QualityWarning],
        skipped: list[str],
        comparisons: int,
    ) -> DuplicateScanResult:
        redundant_chars = sum(group.estimated_redundant_characters for group in groups)
        redundant_tokens = sum(group.estimated_redundant_tokens for group in groups)
        total_chars = sum(len(document.normalized_content) for document in docs) + sum(
            len(chunk.normalized_content) for chunk in chunks
        )
        return DuplicateScanResult(
            groups=sorted(groups, key=lambda group: (group.category, group.id)),
            findings=sorted(findings, key=lambda finding: finding.fingerprint),
            warnings=warnings,
            skipped_item_ids=sorted(set(skipped)),
            statistics=DuplicateStatistics(
                total_documents=len(docs),
                total_chunks=len(chunks),
                document_groups=sum(group.category.endswith("document") for group in groups),
                chunk_groups=sum(
                    group.category == "exact_duplicate_chunk"
                    or group.category == "near_duplicate_chunk"
                    for group in groups
                ),
                repeated_chunk_groups=sum(
                    group.category == "repeated_chunk_within_document" for group in groups
                ),
                candidate_comparisons=comparisons,
                duplicate_content_percentage=min(
                    100.0, redundant_chars / max(1, total_chars) * 100
                ),
                estimated_redundant_characters=redundant_chars,
                estimated_redundant_tokens=redundant_tokens,
            ),
            scanner_name=self.name,
            scanner_version=self.version,
            metadata={
                "offline": True,
                "files_modified": False,
                "token_savings_are_estimates": True,
            },
        )


class NearDuplicateScanner(ExactDuplicateScanner):
    name = "near_duplicate_scanner"
    version = "1.2.0"

    def __init__(
        self,
        config: NearDuplicateConfig | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.near_config = config or NearDuplicateConfig()
        super().__init__(self.near_config, monotonic_clock)

    def scan(
        self,
        documents: list[Document],
        normalized: dict[str, NormalizationResult],
        chunks: list[Chunk],
    ) -> DuplicateScanResult:
        started = self._monotonic()
        warnings: list[QualityWarning] = []
        skipped: list[str] = []
        docs = sorted(documents, key=lambda item: item.id)[: self.near_config.maximum_documents]
        chunk_values = sorted(chunks, key=lambda item: (item.document_id, item.index, item.id))[
            : self.near_config.maximum_chunks
        ]
        items: list[_Item] = []
        for item in self._items(docs, normalized, chunk_values, skipped):
            if len(item.text.strip()) < self.near_config.minimum_comparison_characters:
                skipped.append(item.item_id)
            else:
                items.append(item)
        boilerplate = self._boilerplate_texts(normalized.values())
        signatures: dict[str, set[str]] = {}
        buckets: defaultdict[str, list[str]] = defaultdict(list)
        item_by_id = {item.item_id: item for item in items}
        for item in items:
            cleaned = self._remove_boilerplate(item.text, boilerplate)
            shingles = self._shingles(cleaned)
            if not shingles:
                skipped.append(item.item_id)
                continue
            signatures[item.item_id] = shingles
            for key in sorted(
                hashlib.sha256(shingle.encode()).hexdigest()[:8] for shingle in shingles
            )[:64]:
                if len(buckets[key]) < self.near_config.maximum_bucket_size:
                    buckets[key].append(item.item_id)
        candidates: set[tuple[str, str]] = set()
        for ids in buckets.values():
            ordered = sorted(set(ids))
            for left_index, left in enumerate(ordered):
                for right in ordered[left_index + 1 :]:
                    if item_by_id[left].item_type is item_by_id[right].item_type:
                        candidates.add((left, right))
                        if len(candidates) >= self.near_config.maximum_candidate_comparisons:
                            break
                if len(candidates) >= self.near_config.maximum_candidate_comparisons:
                    break
            if len(candidates) >= self.near_config.maximum_candidate_comparisons:
                warnings.append(
                    QualityWarning(
                        code="maximum_candidate_comparisons_reached",
                        message="Near-duplicate comparisons were bounded.",
                    )
                )
                break
        adjacency: defaultdict[str, set[str]] = defaultdict(set)
        similarity: dict[tuple[str, str], float] = {}
        compared = 0
        for left, right in sorted(candidates):
            if self._monotonic() - started >= self.near_config.maximum_processing_seconds:
                warnings.append(
                    QualityWarning(
                        code="processing_time_limit_reached",
                        message="Near-duplicate scan reached its cooperative time limit.",
                    )
                )
                break
            compared += 1
            score = self._similarity(signatures[left], signatures[right])
            if score >= self.near_config.similarity_threshold and score < 1.0:
                adjacency[left].add(right)
                adjacency[right].add(left)
                similarity[(left, right)] = score
        groups: list[DuplicateGroup] = []
        visited: set[str] = set()
        for item_id in sorted(adjacency):
            if item_id in visited:
                continue
            stack = [item_id]
            component: set[str] = set()
            while stack:
                current = stack.pop()
                if current in component:
                    continue
                component.add(current)
                stack.extend(sorted(adjacency[current] - component))
            visited.update(component)
            members = sorted((item_by_id[value] for value in component), key=self._canonical_key)
            pair_scores = [
                score
                for pair, score in similarity.items()
                if pair[0] in component and pair[1] in component
            ]
            category = (
                "near_duplicate_document"
                if members[0].item_type is DuplicateItemType.DOCUMENT
                else "near_duplicate_chunk"
            )
            group = self._group(
                category,
                _stable_hash("near-signature", sorted(component)),
                members,
                min(pair_scores),
            )
            canonical_shingles = signatures[members[0].item_id]
            shared = canonical_shingles.intersection(
                *[signatures[member.item_id] for member in members[1:]]
            )
            group.metadata["shared_phrases"] = [
                _safe_evidence(value, 200) for value in sorted(shared)[:5]
            ]
            groups.append(group)
            if len(groups) >= self.near_config.maximum_groups:
                warnings.append(
                    QualityWarning(
                        code="maximum_groups_reached", message="Near-duplicate groups were bounded."
                    )
                )
                break
        findings = [
            self._near_finding(group, item_by_id)
            for group in groups[: self.near_config.maximum_findings]
        ]
        return self._result(docs, chunk_values, groups, findings, warnings, skipped, compared)

    def _shingles(self, value: str) -> set[str]:
        tokens = [token.casefold() for token in _WORD.findall(value)]
        size = self.near_config.shingle_size
        if len(tokens) < size:
            return set()
        return {
            " ".join(tokens[index : index + size])
            for index in range(
                min(len(tokens) - size + 1, self.near_config.maximum_shingles_per_item)
            )
        }

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        return len(left & right) / max(1, len(left | right))

    @staticmethod
    def _similarity(left: set[str], right: set[str]) -> float:
        intersection = len(left & right)
        jaccard = intersection / max(1, len(left | right))
        containment = intersection / max(1, min(len(left), len(right)))
        size_balance = min(len(left), len(right)) / max(1, max(len(left), len(right)))
        left_tokens = {token for shingle in left for token in shingle.split()}
        right_tokens = {token for shingle in right for token in shingle.split()}
        token_jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
        return max(jaccard, containment * size_balance, token_jaccard * 0.9)

    @staticmethod
    def _boilerplate_texts(results: Iterable[NormalizationResult]) -> set[str]:
        return {
            annotation.normalized_text.casefold()
            for result in results
            for annotation in result.annotations
            if annotation.annotation_type
            in {
                AnnotationType.BOILERPLATE_CANDIDATE,
                AnnotationType.HEADER_CANDIDATE,
                AnnotationType.FOOTER_CANDIDATE,
                AnnotationType.PAGE_NUMBER_CANDIDATE,
            }
            and annotation.normalized_text
        }

    @staticmethod
    def _remove_boilerplate(value: str, boilerplate: set[str]) -> str:
        return "\n".join(
            line
            for line in value.splitlines()
            if " ".join(line.casefold().split()) not in boilerplate
            and not _PAGE_NUMBER.fullmatch(line)
        )

    def _near_finding(self, group: DuplicateGroup, items: dict[str, _Item]) -> Finding:
        item = items[group.canonical_item_id]
        return _finding(
            scanner=self.name,
            version=self.version,
            rule_id="QUALITY-NEAR-DUPLICATE",
            category=group.category,
            title="Near-duplicate content group",
            description="Items have high lexical shingle similarity after boilerplate-aware comparison.",
            severity=Severity.LOW,
            confidence=group.similarity,
            classification=EvaluationClassification.PROBABLE,
            source=item.source,
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            evidence=_safe_evidence(item.text, self.near_config.maximum_evidence_length),
            impact="Near-identical content may waste retrieval capacity or over-weight one statement.",
            recommendation="Review the group manually; similarity is not proof that an item should be deleted.",
            metadata={
                "group_id": group.id,
                "canonical_item_id": group.canonical_item_id,
                "related_item_ids": [member.item_id for member in group.members[1:]],
                "similarity": group.similarity,
                "method": "bounded_size_balanced_token_shingles",
                "estimated_redundant_tokens": group.estimated_redundant_tokens,
            },
            observed_at=item.observed_at,
        )


class ChunkQualityScanner:
    name = "chunk_quality_scanner"
    version = "1.3.0"

    def __init__(
        self,
        config: ChunkQualityConfig | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.config = config or ChunkQualityConfig()
        self._monotonic = monotonic_clock or monotonic

    def scan(
        self,
        documents: list[Document],
        chunks: list[Chunk],
        normalized: dict[str, NormalizationResult],
    ) -> ChunkQualityResult:
        started = self._monotonic()
        warnings: list[QualityWarning] = []
        skipped: list[str] = []
        values = sorted(chunks, key=lambda chunk: (chunk.document_id, chunk.index, chunk.id))
        if len(values) > self.config.maximum_chunks:
            skipped.extend(chunk.id for chunk in values[self.config.maximum_chunks :])
            values = values[: self.config.maximum_chunks]
            warnings.append(
                QualityWarning(code="maximum_chunks_reached", message="Quality input was bounded.")
            )
        docs = {document.id: document for document in documents}
        token_values = [chunk.token_count for chunk in values]
        collection_median = statistics.median(token_values) if token_values else 0.0
        chunks_by_document: defaultdict[str, list[Chunk]] = defaultdict(list)
        for chunk in values:
            chunks_by_document[chunk.document_id].append(chunk)
        document_medians = {
            document_id: statistics.median(item.token_count for item in document_chunks)
            for document_id, document_chunks in chunks_by_document.items()
        }
        document_positions: dict[str, int] = {}
        forced_run_positions: dict[str, int] = {}
        for document_chunks in chunks_by_document.values():
            for position, chunk in enumerate(document_chunks):
                document_positions[chunk.id] = position
                previous = document_chunks[position - 1] if position else None
                same_forced_run = (
                    chunk.metadata.get("forced_split") is True
                    and previous is not None
                    and previous.metadata.get("forced_split") is True
                    and _forced_split_signature(previous) == _forced_split_signature(chunk)
                )
                forced_run_positions[chunk.id] = (
                    forced_run_positions[previous.id] + 1 if same_forced_run and previous else 0
                )
        findings: list[Finding] = []
        scores: dict[str, ChunkQualityScore] = {}
        redundant_tokens = 0
        broken_ids: set[str] = set()
        boilerplate = NearDuplicateScanner._boilerplate_texts(normalized.values())
        for index, chunk in enumerate(values):
            if self._monotonic() - started >= self.config.maximum_processing_seconds:
                warnings.append(
                    QualityWarning(
                        code="processing_time_limit_reached",
                        message="Quality scan reached its cooperative time limit.",
                    )
                )
                skipped.extend(value.id for value in values[index:])
                break
            document = docs.get(chunk.document_id)
            if document is None:
                skipped.append(chunk.id)
                continue
            document_chunks = chunks_by_document[chunk.document_id]
            issues = self._issues(
                chunk,
                document_medians[chunk.document_id],
                boilerplate,
                document_chunk_count=len(document_chunks),
                document_chunk_position=document_positions[chunk.id],
                forced_run_position=forced_run_positions[chunk.id],
            )
            if index > 0 and values[index - 1].document_id == chunk.document_id:
                overlap_issue, overlap_tokens = self._overlap_issue(values[index - 1], chunk)
                if overlap_issue:
                    issues.append(overlap_issue)
                    redundant_tokens += overlap_tokens
            for issue in issues:
                findings.append(self._issue_finding(document, chunk, issue))
                if issue[3] == "structure":
                    broken_ids.add(chunk.id)
                if len(findings) >= self.config.maximum_findings:
                    warnings.append(
                        QualityWarning(
                            code="maximum_findings_reached",
                            message="Quality findings were bounded.",
                        )
                    )
                    break
            scores[chunk.id] = self._score(issues)
            if len(findings) >= self.config.maximum_findings:
                break
        for document_id, document_chunks in sorted(chunks_by_document.items()):
            document = docs.get(document_id)
            upstream_chunks = [chunk for chunk in document_chunks if not _is_generated_chunk(chunk)]
            if (
                document
                and upstream_chunks
                and len(upstream_chunks) / max(1, len(document.normalized_content) / 1_000)
                > self.config.excessive_chunk_count_per_1k_chars
            ):
                issue = (
                    "excessive_chunk_count",
                    Severity.LOW,
                    "A small document produced an unusually high chunk count.",
                    "efficiency",
                    {"chunk_count": len(document_chunks)},
                )
                findings.append(self._issue_finding(document, upstream_chunks[0], issue))
        oversized = sum(chunk.token_count > self.config.maximum_chunk_tokens for chunk in values)
        undersized = sum("undersized_chunk" in score.explanation for score in scores.values())
        empty = sum(not chunk.normalized_content.strip() for chunk in values)
        return ChunkQualityResult(
            findings=sorted(
                findings[: self.config.maximum_findings],
                key=lambda finding: (
                    finding.document_id or "",
                    finding.chunk_id or "",
                    finding.rule_id,
                ),
            ),
            scores=scores,
            warnings=warnings,
            skipped_chunk_ids=sorted(set(skipped)),
            statistics=ChunkQualityStatistics(
                total_chunks=len(values),
                oversized_chunks=oversized,
                undersized_chunks=undersized,
                empty_chunks=empty,
                structurally_broken_chunks=len(broken_ids),
                average_chunk_tokens=sum(token_values) / max(1, len(token_values)),
                median_chunk_tokens=float(collection_median),
                estimated_redundant_tokens=redundant_tokens,
            ),
            scanner_name=self.name,
            scanner_version=self.version,
            metadata={
                "offline": True,
                "files_modified": False,
                "score_is_product_defined": True,
                "token_savings_are_estimates": True,
            },
        )

    def _issues(
        self,
        chunk: Chunk,
        median: float,
        boilerplate: set[str],
        *,
        document_chunk_count: int,
        document_chunk_position: int,
        forced_run_position: int,
    ) -> list[tuple[str, Severity, str, str, dict[str, Any]]]:
        text = chunk.normalized_content
        stripped = text.strip()
        issues: list[tuple[str, Severity, str, str, dict[str, Any]]] = []
        add = issues.append
        generated = _is_generated_chunk(chunk)
        forced_split = chunk.metadata.get("forced_split") is True
        if not stripped:
            add(("empty_chunk", Severity.HIGH, "Chunk has no usable content.", "content", {}))
            return issues
        if chunk.token_count > self.config.maximum_chunk_tokens:
            add(
                (
                    "oversized_chunk",
                    Severity.MEDIUM,
                    "Chunk exceeds the configured maximum token count.",
                    "size",
                    {"tokens": chunk.token_count},
                )
            )
        elif (
            document_chunk_count > 1
            and not generated
            and chunk.token_count < self.config.minimum_chunk_tokens
        ):
            add(
                (
                    "undersized_chunk",
                    Severity.LOW,
                    "Chunk is below the configured minimum token count.",
                    "size",
                    {"tokens": chunk.token_count},
                )
            )
        if (
            document_chunk_count > 1
            and not generated
            and median
            and chunk.token_count > median * self.config.outlier_factor
        ):
            add(
                (
                    "extreme_size_outlier",
                    Severity.LOW,
                    "Chunk is an extreme size outlier in this collection.",
                    "size",
                    {"median": median},
                )
            )
        maximum_chars = int(chunk.metadata.get("maximum_characters", 100_000))
        if not generated and len(text) >= maximum_chars * self.config.near_character_limit_ratio:
            add(
                (
                    "near_character_limit",
                    Severity.LOW,
                    "Chunk is near its hard character limit.",
                    "size",
                    {"characters": len(text)},
                )
            )
        metadata_flags = {
            "table_present": "table_split",
            "code_block_present": "code_block_split",
            "list_present": "list_split",
        }
        if forced_split and forced_run_position == 0:
            specific_splits = [
                issue_id for key, issue_id in metadata_flags.items() if chunk.metadata.get(key)
            ]
            for issue_id in specific_splits or ["forced_split"]:
                add(
                    (
                        issue_id,
                        Severity.MEDIUM,
                        f"Chunk metadata indicates {issue_id.replace('_', ' ')}.",
                        "structure",
                        {},
                    )
                )
        if _is_generated_heading_only_chunk(chunk):
            return issues
        assess_start_boundary = (not generated and document_chunk_position > 0) or (
            generated and forced_split and forced_run_position == 1
        )
        if assess_start_boundary and stripped[0].islower():
            add(
                (
                    "middle_sentence_start",
                    Severity.LOW,
                    "Chunk begins like a sentence continuation.",
                    "structure",
                    {},
                )
            )
        assess_end_boundary = (
            not generated and document_chunk_position < document_chunk_count - 1
        ) or (generated and forced_split and forced_run_position == 0)
        if (
            assess_end_boundary
            and stripped[-1].isalnum()
            and not stripped.endswith(_SENTENCE_BOUNDARY_ENDINGS)
        ):
            add(
                (
                    "middle_sentence_end",
                    Severity.LOW,
                    "Chunk ends without a clear sentence or structural boundary.",
                    "structure",
                    {},
                )
            )
        if all(not character.isalnum() for character in stripped):
            add(
                (
                    "punctuation_only_chunk",
                    Severity.MEDIUM,
                    "Chunk contains punctuation only.",
                    "content",
                    {},
                )
            )
        elif stripped.isnumeric():
            normalized_line = " ".join(stripped.casefold().split())
            if normalized_line in boilerplate or not generated or forced_split:
                add(
                    (
                        (
                            "page_number_only_chunk"
                            if normalized_line in boilerplate and _PAGE_NUMBER.fullmatch(stripped)
                            else "numeric_only_chunk"
                        ),
                        Severity.LOW,
                        "Chunk contains only numeric/page-marker content.",
                        "content",
                        {},
                    )
                )
            return issues
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        tokens = [token.casefold() for token in _WORD.findall(text)]
        repeated_lines = (
            len(tokens) >= self.config.minimum_lexical_sample_tokens
            and len(lines) >= 3
            and max(Counter(lines).values()) / len(lines) >= 0.6
        )
        if repeated_lines:
            add(
                (
                    "repeated_line_chunk",
                    Severity.LOW,
                    "Chunk repeats the same line excessively.",
                    "content",
                    {},
                )
            )
        boilerplate_chars = sum(
            len(line)
            for line in lines
            if line.casefold() in boilerplate or _PAGE_NUMBER.fullmatch(line)
        )
        boilerplate_dominated = (
            boilerplate_chars / max(1, len(stripped)) >= self.config.boilerplate_dominance_threshold
        )
        if boilerplate_dominated:
            add(
                (
                    "boilerplate_dominated_chunk",
                    Severity.LOW,
                    "Chunk is dominated by detected boilerplate.",
                    "content",
                    {},
                )
            )
        printable_ratio = sum(
            character.isprintable() or character in "\n\t" for character in text
        ) / max(1, len(text))
        if printable_ratio < 0.85:
            add(
                (
                    "low_printable_ratio",
                    Severity.MEDIUM,
                    "Chunk has a low printable-character ratio.",
                    "extraction",
                    {"ratio": printable_ratio},
                )
            )
        if len(_CONTROL_MARKER.findall(text)) / max(1, len(_TOKEN.findall(text))) > 0.05:
            add(
                (
                    "excessive_control_markers",
                    Severity.MEDIUM,
                    "Chunk contains excessive visible control markers.",
                    "extraction",
                    {},
                )
            )
        protected_structure = bool(
            chunk.metadata.get("code_block_present") or chunk.metadata.get("table_present")
        )
        if (
            len(tokens) >= self.config.minimum_lexical_sample_tokens
            and not protected_structure
            and not repeated_lines
            and not boilerplate_dominated
        ):
            most_common = max(Counter(tokens).values()) / len(tokens)
            density = len(set(tokens)) / len(tokens)
            if most_common >= self.config.repeated_token_threshold:
                add(
                    (
                        "highly_repetitive_tokens",
                        Severity.LOW,
                        "One token dominates the chunk.",
                        "content",
                        {"ratio": most_common},
                    )
                )
            elif density < self.config.information_density_threshold:
                add(
                    (
                        "low_information_density",
                        Severity.LOW,
                        "Chunk has very low lexical information density.",
                        "content",
                        {"density": density},
                    )
                )
        replacement_count = text.count("�") + text.count("<REPLACEMENT>")
        if replacement_count >= 3 or replacement_count / max(1, len(text)) > 0.02:
            add(
                (
                    "garbled_extraction",
                    Severity.MEDIUM,
                    "Chunk contains garbled extraction indicators.",
                    "extraction",
                    {
                        "replacement_count": replacement_count,
                        "ratio": replacement_count / max(1, len(text)),
                    },
                )
            )
        return issues

    def _overlap_issue(
        self, previous: Chunk, current: Chunk
    ) -> tuple[tuple[str, Severity, str, str, dict[str, Any]] | None, int]:
        if _is_generated_chunk(previous) and _is_generated_chunk(current):
            return None, 0
        left = [token.casefold() for token in _WORD.findall(previous.normalized_content)]
        right = [token.casefold() for token in _WORD.findall(current.normalized_content)]
        maximum = min(len(left), len(right))
        overlap = 0
        for size in range(1, maximum + 1):
            if left[-size:] == right[:size]:
                overlap = size
        ratio = overlap / max(1, len(right))
        if ratio >= self.config.overlap_warning_threshold:
            return (
                "excessive_overlap",
                Severity.MEDIUM,
                "Overlap consumes too much of the useful chunk content.",
                "overlap",
                {"overlap_tokens": overlap, "ratio": ratio},
            ), overlap
        if left and right and self._token_jaccard(left, right) >= 0.9:
            return (
                "near_identical_neighbor_chunks",
                Severity.LOW,
                "Adjacent chunks are nearly identical.",
                "overlap",
                {"similarity": self._token_jaccard(left, right)},
            ), min(len(left), len(right))
        return None, 0

    @staticmethod
    def _token_jaccard(left: list[str], right: list[str]) -> float:
        a, b = set(left), set(right)
        return len(a & b) / max(1, len(a | b))

    def _issue_finding(
        self,
        document: Document,
        chunk: Chunk,
        issue: tuple[str, Severity, str, str, dict[str, Any]],
    ) -> Finding:
        issue_id, severity, description, dimension, details = issue
        return _finding(
            scanner=self.name,
            version=self.version,
            rule_id=f"QUALITY-CHUNK-{issue_id.upper().replace('_', '-')}",
            category="chunk_quality",
            title=issue_id.replace("_", " ").title(),
            description=description,
            severity=severity,
            confidence=0.95 if details or issue_id in {"empty_chunk", "forced_split"} else 0.8,
            classification=EvaluationClassification.CONFIRMED
            if issue_id in {"empty_chunk", "forced_split", "oversized_chunk"}
            else EvaluationClassification.PROBABLE,
            source=chunk.source,
            document_id=document.id,
            chunk_id=chunk.id,
            evidence=_safe_evidence(chunk.normalized_content, self.config.maximum_evidence_length),
            impact="Poor chunk quality can reduce retrieval precision, waste context, or hide source structure.",
            recommendation=self._recommendation(issue_id),
            metadata={"dimension": dimension, "details": details, "automatic_modification": False},
            observed_at=document.ingested_at,
        )

    @staticmethod
    def _recommendation(issue_id: str) -> str:
        if "oversized" in issue_id or "split" in issue_id or "limit" in issue_id:
            return "Rechunk with safer structural boundaries and review the affected source."
        if "undersized" in issue_id:
            return "Consider merging with a related adjacent chunk while preserving headings."
        if "overlap" in issue_id or "identical" in issue_id:
            return "Reduce bounded overlap without crossing unrelated structural boundaries."
        if "mapping" in issue_id or "extraction" in issue_id or "garbled" in issue_id:
            return "Reparse the source and inspect extraction/mapping warnings."
        if "boilerplate" in issue_id:
            return "Review boilerplate policy before indexing; do not remove content automatically."
        return "Review the chunk and adjust deterministic chunking configuration if appropriate."

    @staticmethod
    def _score(issues: list[tuple[str, Severity, str, str, dict[str, Any]]]) -> ChunkQualityScore:
        penalties: defaultdict[str, float] = defaultdict(float)
        weights = {
            Severity.LOW: 8,
            Severity.MEDIUM: 18,
            Severity.HIGH: 35,
            Severity.CRITICAL: 50,
            Severity.INFO: 2,
        }
        mapping = {
            "size": "size_quality",
            "structure": "structural_integrity",
            "content": "information_density",
            "overlap": "overlap_efficiency",
            "mapping": "source_mapping_quality",
            "extraction": "extraction_quality",
            "efficiency": "overlap_efficiency",
        }
        explanations: list[str] = []
        for issue_id, severity, _, dimension, _ in issues:
            penalties[mapping.get(dimension, "information_density")] += weights[severity]
            explanations.append(issue_id)
        values = {
            name: max(0.0, 100.0 - penalties[name])
            for name in {
                "size_quality",
                "structural_integrity",
                "information_density",
                "overlap_efficiency",
                "source_mapping_quality",
                "extraction_quality",
            }
        }
        overall = sum(values.values()) / len(values)
        return ChunkQualityScore(overall=overall, explanation=sorted(explanations), **values)
