"""Deterministic duplicate and chunk-quality scanner tests."""

from datetime import UTC, datetime
from typing import Any

import pytest
from ragscanner.domain import Chunk, Document, SourceLocation
from ragscanner.domain.helpers import document_content_hash
from ragscanner.normalization import DocumentNormalizer
from ragscanner.quality import (
    ChunkQualityConfig,
    ChunkQualityScanner,
    DuplicateScanConfig,
    ExactDuplicateScanner,
    NearDuplicateConfig,
    NearDuplicateScanner,
)

NOW = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)


def doc(identifier: str, content: str, path: str | None = None) -> Document:
    return Document(
        id=identifier,
        source=SourceLocation(
            source_id="local",
            source_type="filesystem",
            source_name="local",
            source_path=path or f"{identifier}.txt",
            line_start=1,
            line_end=max(1, content.count("\n") + 1),
        ),
        content=content,
        normalized_content=content,
        content_hash=document_content_hash(content),
        mime_type="text/plain",
        ingested_at=NOW,
    )


def normalized(documents: list[Document]):  # type: ignore[no-untyped-def]
    return {document.id: DocumentNormalizer().normalize(document) for document in documents}


def chunk(
    identifier: str,
    document_id: str,
    index: int,
    text: str,
    *,
    tokens: int | None = None,
    metadata: dict[str, Any] | None = None,
    headings: list[str] | None = None,
) -> Chunk:
    return Chunk(
        id=identifier,
        document_id=document_id,
        index=index,
        content=text,
        normalized_content=text,
        content_hash=document_content_hash(text),
        token_count=tokens if tokens is not None else len(text.split()),
        character_count=len(text),
        source=SourceLocation(
            source_id="local",
            source_type="filesystem",
            source_name="local",
            source_path=f"{document_id}.txt",
            line_start=1,
            line_end=max(1, text.count("\n") + 1),
        ),
        headings=headings or [],
        metadata=metadata or {},
    )


def finding_rules(result) -> set[str]:  # type: ignore[no-untyped-def]
    return {finding.rule_id for finding in result.findings}


def test_exact_document_duplicates_formatting_canonical_and_stability() -> None:
    docs = [
        doc("b", "Same   normalized content", "z.txt"),
        doc("a", "Same normalized content", "a.txt"),
    ]
    results = normalized(docs)
    scanner = ExactDuplicateScanner()
    first = scanner.scan(docs, results, [])
    second = scanner.scan(list(reversed(docs)), results, [])
    assert len(first.groups) == 1
    assert first.groups[0].category == "exact_duplicate_document"
    assert first.groups[0].canonical_item_id == "a"
    assert first.groups[0].id == second.groups[0].id
    assert first.findings[0].fingerprint == second.findings[0].fingerprint
    assert first.groups[0].metadata["automatic_deletion_recommended"] is False


def test_exact_chunk_duplicates_and_repeated_chunk_within_document() -> None:
    docs = [doc("d1", "body"), doc("d2", "body 2")]
    values = [
        chunk("c1", "d1", 0, "identical chunk text"),
        chunk("c2", "d1", 1, "identical chunk text"),
        chunk("c3", "d2", 0, "cross document duplicate"),
        chunk("c4", "d1", 2, "cross document duplicate"),
    ]
    result = ExactDuplicateScanner().scan(docs, normalized(docs), values)
    assert {group.category for group in result.groups} == {
        "repeated_chunk_within_document",
        "exact_duplicate_chunk",
    }
    assert len(result.findings) == 2


def test_empty_exact_content_excluded_and_limits_warn() -> None:
    docs = [doc("a", ""), doc("b", ""), doc("c", "unique")]
    result = ExactDuplicateScanner(DuplicateScanConfig(maximum_documents=2)).scan(
        docs, normalized(docs), []
    )
    assert result.groups == []
    assert "c" in result.skipped_item_ids
    assert {warning.code for warning in result.warnings} == {"maximum_documents_reached"}


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (
            "RAG sistemleri belgeleri küçük parçalara ayırır ve arama sırasında ilgili parçaları getirir.",
            "RAG sistemleri belgeleri küçük parçalara böler ve sorgu sırasında ilgili parçaları getirir.",
        ),
        (
            "Retrieval systems split documents into useful chunks and return relevant context for questions.",
            "Retrieval systems split documents into useful chunks and return highly relevant context for user questions.",
        ),
        (
            "Türkçe English mixed retrieval context preserves source location and document identity for analysis.",
            "Türkçe English mixed retrieval context preserves source location and stable document identity for analysis.",
        ),
    ],
)
def test_near_duplicate_multilingual_lexical_similarity(left: str, right: str) -> None:
    docs = [doc("a", left), doc("b", right)]
    config = NearDuplicateConfig(
        similarity_threshold=0.5,
        shingle_size=3,
        minimum_comparison_characters=40,
    )
    result = NearDuplicateScanner(config).scan(docs, normalized(docs), [])
    assert len(result.groups) == 1
    assert 0.5 <= result.groups[0].similarity < 1
    assert result.findings[0].metadata["method"] == "bounded_token_shingle_jaccard"


def test_near_duplicate_threshold_short_and_boilerplate_controls() -> None:
    docs = [
        doc("a", "CONFIDENTIAL\nPage 1\nAlpha unique body about apples and pears."),
        doc("b", "CONFIDENTIAL\nPage 2\nCompletely unrelated body about engines and wheels."),
        doc("short", "common heading"),
    ]
    config = NearDuplicateConfig(
        similarity_threshold=0.7,
        shingle_size=3,
        minimum_comparison_characters=30,
        maximum_candidate_comparisons=1,
    )
    result = NearDuplicateScanner(config).scan(docs, normalized(docs), [])
    assert result.groups == []
    assert "short" in result.skipped_item_ids
    assert result.statistics.candidate_comparisons <= 1


def test_near_duplicate_groups_deterministically_and_suppresses_exact_pairs() -> None:
    base = "one two three four five six seven eight nine ten eleven twelve"
    docs = [doc("a", base), doc("b", base + " thirteen"), doc("c", base + " fourteen")]
    config = NearDuplicateConfig(
        similarity_threshold=0.6,
        shingle_size=3,
        minimum_comparison_characters=20,
    )
    scanner = NearDuplicateScanner(config)
    first = scanner.scan(docs, normalized(docs), [])
    second = scanner.scan(list(reversed(docs)), normalized(docs), [])
    assert len(first.groups) == 1
    assert first.groups[0].id == second.groups[0].id
    exact_docs = [doc("x", base), doc("y", base)]
    assert NearDuplicateScanner(config).scan(exact_docs, normalized(exact_docs), []).groups == []


def test_near_duplicate_candidate_limit_warning_on_synthetic_collection() -> None:
    docs = [
        doc(f"d{index}", f"shared one two three four five six unique {index} trailing text")
        for index in range(30)
    ]
    result = NearDuplicateScanner(
        NearDuplicateConfig(
            similarity_threshold=0.6,
            shingle_size=2,
            minimum_comparison_characters=20,
            maximum_candidate_comparisons=5,
        )
    ).scan(docs, normalized(docs), [])
    assert result.statistics.candidate_comparisons <= 5
    assert "maximum_candidate_comparisons_reached" in {warning.code for warning in result.warnings}


def test_chunk_size_empty_and_outlier_findings_and_scores() -> None:
    document = doc("d", "body")
    chunks = [
        chunk("empty", "d", 0, "", tokens=0),
        chunk("small", "d", 1, "short prose.", tokens=2),
        chunk("valid", "d", 2, "Healthy complete prose with enough useful information.", tokens=8),
        chunk("large", "d", 3, "word " * 80, tokens=80),
    ]
    result = ChunkQualityScanner(
        ChunkQualityConfig(
            minimum_chunk_tokens=3,
            target_chunk_tokens=10,
            maximum_chunk_tokens=20,
            outlier_factor=2,
        )
    ).scan([document], chunks, normalized([document]))
    rules = finding_rules(result)
    assert "QUALITY-CHUNK-EMPTY-CHUNK" in rules
    assert "QUALITY-CHUNK-UNDERSIZED-CHUNK" in rules
    assert "QUALITY-CHUNK-OVERSIZED-CHUNK" in rules
    assert "QUALITY-CHUNK-EXTREME-SIZE-OUTLIER" in rules
    assert all(0 <= score.overall <= 100 for score in result.scores.values())
    assert result.metadata["score_is_product_defined"] is True


def test_structural_metadata_findings_and_healthy_structure() -> None:
    document = doc("d", "body")
    broken = chunk(
        "broken",
        "d",
        1,
        "continuation without ending",
        metadata={
            "forced_split": True,
            "table_present": True,
            "code_block_present": True,
            "list_present": True,
            "approximate_source_mapping": True,
        },
    )
    healthy = chunk(
        "healthy",
        "d",
        0,
        "A complete and healthy paragraph ends correctly.",
        headings=["# Healthy"],
    )
    result = ChunkQualityScanner(
        ChunkQualityConfig(minimum_chunk_tokens=0, target_chunk_tokens=20, maximum_chunk_tokens=50)
    ).scan([document], [healthy, broken], normalized([document]))
    rules = finding_rules(result)
    assert {
        "QUALITY-CHUNK-FORCED-SPLIT",
        "QUALITY-CHUNK-TABLE-SPLIT",
        "QUALITY-CHUNK-CODE-BLOCK-SPLIT",
        "QUALITY-CHUNK-LIST-SPLIT",
        "QUALITY-CHUNK-APPROXIMATE-MAPPING",
        "QUALITY-CHUNK-MIDDLE-SENTENCE-START",
        "QUALITY-CHUNK-MIDDLE-SENTENCE-END",
    }.issubset(rules)
    assert not any(finding.chunk_id == "healthy" for finding in result.findings)


@pytest.mark.parametrize(
    ("identifier", "text", "expected"),
    [
        ("punct", "!!! --- ???", "QUALITY-CHUNK-PUNCTUATION-ONLY-CHUNK"),
        ("numeric", "123456789", "QUALITY-CHUNK-PAGE-NUMBER-ONLY-CHUNK"),
        ("repeat", "same line\nsame line\nsame line\nother", "QUALITY-CHUNK-REPEATED-LINE-CHUNK"),
        ("replacement", "useful � � � corrupted text", "QUALITY-CHUNK-GARBLED-EXTRACTION"),
        ("control", "<ZWSP> <ZWSP> content", "QUALITY-CHUNK-EXCESSIVE-CONTROL-MARKERS"),
        ("tokens", "repeat repeat repeat repeat other", "QUALITY-CHUNK-HIGHLY-REPETITIVE-TOKENS"),
    ],
)
def test_content_quality_signals(identifier: str, text: str, expected: str) -> None:
    document = doc("d", "body")
    result = ChunkQualityScanner(
        ChunkQualityConfig(minimum_chunk_tokens=0, target_chunk_tokens=20, maximum_chunk_tokens=50)
    ).scan([document], [chunk(identifier, "d", 0, text)], normalized([document]))
    assert expected in finding_rules(result)


def test_overlap_duplicate_neighbors_and_unrelated_neighbors() -> None:
    document = doc("d", "body")
    first = chunk("a", "d", 0, "alpha beta gamma delta epsilon.")
    overlapping = chunk("b", "d", 1, "gamma delta epsilon new useful words.")
    unrelated = chunk("c", "d", 2, "completely separate topic about databases.")
    result = ChunkQualityScanner(
        ChunkQualityConfig(
            minimum_chunk_tokens=0,
            target_chunk_tokens=20,
            maximum_chunk_tokens=50,
            overlap_warning_threshold=0.4,
        )
    ).scan([document], [first, overlapping, unrelated], normalized([document]))
    overlap_findings = [
        finding
        for finding in result.findings
        if finding.rule_id == "QUALITY-CHUNK-EXCESSIVE-OVERLAP"
    ]
    assert [finding.chunk_id for finding in overlap_findings] == ["b"]
    assert result.statistics.estimated_redundant_tokens == 3
    assert not any(
        finding.chunk_id == "c" and "OVERLAP" in finding.rule_id for finding in result.findings
    )


def test_excessive_chunk_count_limits_secret_masking_and_no_mutation() -> None:
    value = "password=RAGSYNTH_abcdef123456789"  # gitleaks:allow - synthetic fixture
    document = doc("d", value)
    chunks = [chunk(f"c{index}", "d", index, value) for index in range(10)]
    original = [value.model_copy(deep=True) for value in chunks]
    result = ChunkQualityScanner(
        ChunkQualityConfig(
            minimum_chunk_tokens=0,
            target_chunk_tokens=20,
            maximum_chunk_tokens=50,
            maximum_chunks=5,
            maximum_evidence_length=64,
            excessive_chunk_count_per_1k_chars=1,
        )
    ).scan([document], chunks, normalized([document]))
    assert "maximum_chunks_reached" in {warning.code for warning in result.warnings}
    assert "QUALITY-CHUNK-EXCESSIVE-CHUNK-COUNT" in finding_rules(result)
    serialized = json_text = "\n".join(finding.model_dump_json() for finding in result.findings)
    assert "RAGSYNTH_abcdef123456789" not in serialized
    assert all(len(finding.evidence) <= 64 for finding in result.findings)
    assert chunks == original
    assert result.metadata["files_modified"] is False
    assert json_text
