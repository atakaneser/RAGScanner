"""Workload-aware RAG configuration advice tests."""

from datetime import UTC, datetime

from ragscanner.chunking import ChunkingConfig
from ragscanner.domain import Chunk, Document, SourceLocation
from ragscanner.quality import (
    RAGConfigurationAdvisor,
    RAGConfigurationConfig,
    RAGProfile,
)
from ragscanner.quality.models import ChunkQualityStatistics

NOW = datetime(2026, 7, 22, tzinfo=UTC)
SOURCE = SourceLocation(
    source_id="source",
    source_type="filesystem",
    source_name="fixture",
    source_path="fixture.md",
)


def document() -> Document:
    return Document(
        id="document",
        source=SOURCE,
        content="Synthetic document",
        normalized_content="Synthetic document",
        content_hash="0" * 64,
        mime_type="text/markdown",
        ingested_at=NOW,
    )


def chunk(identifier: str, tokens: int, **metadata: bool) -> Chunk:
    return Chunk(
        id=identifier,
        document_id="document",
        index=0,
        content="Synthetic chunk",
        normalized_content="Synthetic chunk",
        content_hash="0" * 64,
        token_count=tokens,
        character_count=15,
        source=SOURCE,
        metadata=metadata,
    )


def stats(*, median: float, undersized: int = 0, broken: int = 0) -> ChunkQualityStatistics:
    return ChunkQualityStatistics(
        total_chunks=4,
        oversized_chunks=0,
        undersized_chunks=undersized,
        empty_chunks=0,
        structurally_broken_chunks=broken,
        average_chunk_tokens=median,
        median_chunk_tokens=median,
        estimated_redundant_tokens=0,
    )


def test_fact_and_long_context_profiles_have_distinct_starting_points() -> None:
    advisor = RAGConfigurationAdvisor()
    fact = advisor.recommend(
        config=RAGConfigurationConfig(profile=RAGProfile.FACT_LOOKUP),
        chunking=ChunkingConfig(),
        documents=[document()],
        chunks=[chunk("one", 100)],
        quality=stats(median=100),
    )
    broad = advisor.recommend(
        config=RAGConfigurationConfig(profile=RAGProfile.LONG_CONTEXT_RESEARCH),
        chunking=ChunkingConfig(),
        documents=[document()],
        chunks=[chunk("one", 700)],
        quality=stats(median=700),
    )

    assert fact.recommended["target_tokens"] == 128
    assert broad.recommended["target_tokens"] == 700
    assert "Recall@k" in broad.validation_metrics
    assert broad.status == "starting_point_requires_retrieval_validation"


def test_advice_prioritizes_structure_and_detects_specialized_content() -> None:
    advice = RAGConfigurationAdvisor().recommend(
        config=RAGConfigurationConfig(profile=RAGProfile.GENERAL_QA),
        chunking=ChunkingConfig(),
        documents=[document()],
        chunks=[
            chunk("table", 80, table_present=True),
            chunk("code", 80, code_block_present=True),
        ],
        quality=stats(median=80, undersized=2, broken=1),
    )

    assert any("structural split" in item for item in advice.actions)
    assert any("table_analytics" in item for item in advice.actions)
    assert any("code_assistant" in item for item in advice.actions)
    assert advice.observed["table_chunks"] == 1
    assert advice.observed["code_chunks"] == 1


def test_embedding_limit_warning_is_explanatory_not_an_automatic_mutation() -> None:
    advice = RAGConfigurationAdvisor().recommend(
        config=RAGConfigurationConfig(
            profile=RAGProfile.LONG_CONTEXT_RESEARCH,
            embedding_context_tokens=1_024,
        ),
        chunking=ChunkingConfig(),
        documents=[document()],
        chunks=[chunk("one", 700)],
        quality=stats(median=700),
    )

    assert advice.recommended["maximum_tokens"] == 1_024
    assert any("headroom" in item for item in advice.actions)
    assert advice.configured["embedding_context_tokens"] == 1_024
