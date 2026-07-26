"""Explainable starting-point configuration advice for different RAG workloads."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ragscanner.chunking import ChunkingConfig, ChunkingStrategy
from ragscanner.domain import Chunk, Document
from ragscanner.quality.models import ChunkQualityStatistics


class RAGProfile(StrEnum):
    FACT_LOOKUP = "fact_lookup"
    GENERAL_QA = "general_qa"
    POLICY_PROCEDURE = "policy_procedure"
    LONG_CONTEXT_RESEARCH = "long_context_research"
    CODE_ASSISTANT = "code_assistant"
    TABLE_ANALYTICS = "table_analytics"


class RAGConfigurationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: RAGProfile = RAGProfile.GENERAL_QA
    embedding_context_tokens: int | None = Field(default=None, ge=128, le=10_000_000)
    generator_context_tokens: int | None = Field(default=None, ge=128, le=10_000_000)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=1_000)


class RAGConfigurationAdvice(BaseModel):
    advisor_version: str = "1.0.0"
    profile: RAGProfile
    status: str = "starting_point_requires_retrieval_validation"
    configured: dict[str, Any]
    recommended: dict[str, Any]
    observed: dict[str, Any]
    actions: list[str] = Field(default_factory=list)
    validation_metrics: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


_PROFILES: dict[RAGProfile, dict[str, Any]] = {
    RAGProfile.FACT_LOOKUP: {
        "minimum_tokens": 40,
        "target_tokens": 128,
        "maximum_tokens": 256,
        "overlap_tokens": 12,
        "retrieval_top_k": 5,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Fine-grained factual retrieval usually benefits from smaller evidence units.",
    },
    RAGProfile.GENERAL_QA: {
        "minimum_tokens": 50,
        "target_tokens": 300,
        "maximum_tokens": 500,
        "overlap_tokens": 30,
        "retrieval_top_k": 5,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Balanced starting point for mixed question types and ordinary documentation.",
    },
    RAGProfile.POLICY_PROCEDURE: {
        "minimum_tokens": 80,
        "target_tokens": 450,
        "maximum_tokens": 700,
        "overlap_tokens": 45,
        "retrieval_top_k": 6,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Procedures need enough neighboring steps and heading context to remain actionable.",
    },
    RAGProfile.LONG_CONTEXT_RESEARCH: {
        "minimum_tokens": 120,
        "target_tokens": 700,
        "maximum_tokens": 1_024,
        "overlap_tokens": 70,
        "retrieval_top_k": 8,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Broad synthesis questions need larger coherent evidence windows.",
    },
    RAGProfile.CODE_ASSISTANT: {
        "minimum_tokens": 80,
        "target_tokens": 600,
        "maximum_tokens": 1_000,
        "overlap_tokens": 60,
        "retrieval_top_k": 6,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Code boundaries and related declarations matter more than arbitrary fixed windows.",
    },
    RAGProfile.TABLE_ANALYTICS: {
        "minimum_tokens": 80,
        "target_tokens": 500,
        "maximum_tokens": 800,
        "overlap_tokens": 0,
        "retrieval_top_k": 5,
        "strategy": ChunkingStrategy.STRUCTURE_AWARE.value,
        "why": "Tables should remain intact; duplicated row overlap can distort numeric retrieval.",
    },
}


class RAGConfigurationAdvisor:
    """Generate advice from an explicit workload profile and observed scan statistics."""

    version = "1.0.0"

    def recommend(
        self,
        *,
        config: RAGConfigurationConfig,
        chunking: ChunkingConfig,
        documents: list[Document],
        chunks: list[Chunk],
        quality: ChunkQualityStatistics | None,
    ) -> RAGConfigurationAdvice:
        profile = dict(_PROFILES[config.profile])
        actions: list[str] = []
        median = quality.median_chunk_tokens if quality is not None else 0.0
        if median and median < profile["minimum_tokens"]:
            actions.append(
                "Observed chunks are more fragmented than this profile; merge adjacent semantic sections and re-evaluate retrieval."
            )
        if median and median > profile["maximum_tokens"]:
            actions.append(
                "Observed chunks are coarser than this profile; reduce size without splitting lists, tables, code, or procedures."
            )
        if quality is not None and quality.structurally_broken_chunks:
            actions.append(
                "Repair structural split findings before tuning token counts; boundary quality takes priority over a numeric target."
            )
        if quality is not None and quality.undersized_chunks > max(1, quality.total_chunks // 4):
            actions.append(
                "More than one quarter of assessed chunks are undersized; review heading-only and fragmented upstream chunks."
            )
        table_chunks = sum(chunk.metadata.get("table_present") is True for chunk in chunks)
        code_chunks = sum(chunk.metadata.get("code_block_present") is True for chunk in chunks)
        if table_chunks and config.profile is not RAGProfile.TABLE_ANALYTICS:
            actions.append(
                "Tables were observed; compare this profile with table_analytics in a retrieval benchmark."
            )
        if code_chunks and config.profile is not RAGProfile.CODE_ASSISTANT:
            actions.append(
                "Code blocks were observed; compare this profile with code_assistant and preserve structural boundaries."
            )
        if (
            config.embedding_context_tokens is not None
            and profile["maximum_tokens"] >= config.embedding_context_tokens
        ):
            actions.append(
                "The profile maximum reaches the declared embedding context limit; leave tokenizer overhead and metadata headroom."
            )
        if not actions:
            actions.append(
                "Use this as an initial candidate, then compare at least one smaller and one larger configuration on representative queries."
            )

        recommended = {
            **profile,
            "retrieval_top_k": config.retrieval_top_k or profile["retrieval_top_k"],
            "preserve_page_boundaries": True,
            "preserve_tables": True,
            "preserve_code_blocks": True,
            "attach_heading_context": True,
        }
        return RAGConfigurationAdvice(
            profile=config.profile,
            configured={
                "strategy": chunking.strategy.value,
                "minimum_tokens": chunking.minimum_token_count,
                "target_tokens": chunking.target_token_count,
                "maximum_tokens": chunking.maximum_token_count,
                "overlap_tokens": chunking.overlap_token_count,
                "embedding_context_tokens": config.embedding_context_tokens,
                "generator_context_tokens": config.generator_context_tokens,
                "retrieval_top_k": config.retrieval_top_k,
            },
            recommended=recommended,
            observed={
                "documents": len(documents),
                "chunks": len(chunks),
                "average_chunk_tokens": quality.average_chunk_tokens if quality else None,
                "median_chunk_tokens": quality.median_chunk_tokens if quality else None,
                "undersized_chunks": quality.undersized_chunks if quality else None,
                "oversized_chunks": quality.oversized_chunks if quality else None,
                "structurally_broken_chunks": quality.structurally_broken_chunks
                if quality
                else None,
                "table_chunks": table_chunks,
                "code_chunks": code_chunks,
            },
            actions=actions,
            validation_metrics=[
                "Recall@k",
                "nDCG@k or MRR",
                "context precision and context recall",
                "answer faithfulness",
                "answer relevance",
                "citation correctness",
                "latency and retrieved-token cost",
            ],
            limitations=[
                "There is no universal best chunk size; workload, document structure, tokenizer, embedding model, and query distribution change the optimum.",
                "Static source analysis cannot prove retrieval or answer quality without representative queries and relevance labels.",
                "Token counts are model-independent approximations unless a production tokenizer is supplied.",
            ],
            references=[
                "https://arxiv.org/abs/2505.21700",
                "https://aclanthology.org/2025.acl-industry.69/",
                "https://aclanthology.org/2025.findings-naacl.114/",
                "https://aclanthology.org/2024.eacl-demo.16/",
                "https://aclanthology.org/2024.naacl-long.20/",
            ],
        )
