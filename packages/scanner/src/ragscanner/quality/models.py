"""Typed contracts for deterministic duplicate and chunk-quality scanners."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ragscanner.domain import Finding, SourceLocation


class DuplicateItemType(StrEnum):
    DOCUMENT = "document"
    CHUNK = "chunk"


class DuplicateMember(BaseModel):
    item_type: DuplicateItemType
    item_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_id: str | None = None
    source: SourceLocation
    normalized_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    character_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    evidence_excerpt: str | None = Field(default=None, max_length=4_096)


class DuplicateGroup(BaseModel):
    id: str = Field(pattern=r"^[a-f0-9]{64}$")
    category: str = Field(min_length=1)
    canonical_item_id: str = Field(min_length=1)
    members: list[DuplicateMember] = Field(min_length=2)
    similarity: float = Field(ge=0, le=1)
    estimated_redundant_characters: int = Field(ge=0)
    estimated_redundant_tokens: int = Field(ge=0)
    matched_content: str | None = Field(default=None, max_length=4_096)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DuplicateScanConfig(BaseModel):
    maximum_documents: int = Field(default=10_000, gt=0)
    maximum_chunks: int = Field(default=100_000, gt=0)
    maximum_groups: int = Field(default=10_000, gt=0)
    maximum_findings: int = Field(default=10_000, gt=0)
    maximum_evidence_length: int = Field(default=256, ge=64, le=4_096)
    minimum_duplicate_chunk_characters: int = Field(default=48, ge=0, le=100_000)
    minimum_duplicate_chunk_tokens: int = Field(default=6, ge=0, le=10_000)
    maximum_processing_seconds: float = Field(default=30, gt=0, le=600)


class NearDuplicateConfig(DuplicateScanConfig):
    similarity_threshold: float = Field(default=0.82, ge=0.5, le=1)
    shingle_size: int = Field(default=5, ge=2, le=12)
    minimum_comparison_characters: int = Field(default=120, ge=20)
    maximum_candidate_comparisons: int = Field(default=100_000, gt=0)
    maximum_shingles_per_item: int = Field(default=10_000, gt=0)
    maximum_bucket_size: int = Field(default=200, ge=2)


class DuplicateStatistics(BaseModel):
    total_documents: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    document_groups: int = Field(ge=0)
    chunk_groups: int = Field(ge=0)
    repeated_chunk_groups: int = Field(ge=0)
    candidate_comparisons: int = Field(ge=0)
    duplicate_content_percentage: float = Field(ge=0, le=100)
    estimated_redundant_characters: int = Field(ge=0)
    estimated_redundant_tokens: int = Field(ge=0)


class DuplicateScanResult(BaseModel):
    groups: list[DuplicateGroup] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    warnings: list[QualityWarning] = Field(default_factory=list)
    skipped_item_ids: list[str] = Field(default_factory=list)
    statistics: DuplicateStatistics
    scanner_name: str = Field(min_length=1)
    scanner_version: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkQualityConfig(BaseModel):
    minimum_chunk_tokens: int = Field(default=50, ge=0)
    target_chunk_tokens: int = Field(default=300, gt=0)
    maximum_chunk_tokens: int = Field(default=500, gt=0)
    near_character_limit_ratio: float = Field(default=0.9, ge=0.5, le=1)
    overlap_warning_threshold: float = Field(default=0.4, ge=0, le=1)
    boilerplate_dominance_threshold: float = Field(default=0.6, ge=0, le=1)
    information_density_threshold: float = Field(default=0.25, ge=0, le=1)
    repeated_token_threshold: float = Field(default=0.55, ge=0, le=1)
    minimum_lexical_sample_tokens: int = Field(default=20, ge=3, le=1_000)
    outlier_factor: float = Field(default=3.0, ge=1.5, le=20)
    excessive_chunk_count_per_1k_chars: float = Field(default=8, gt=0)
    maximum_chunks: int = Field(default=100_000, gt=0)
    maximum_findings: int = Field(default=20_000, gt=0)
    maximum_evidence_length: int = Field(default=256, ge=64, le=4_096)
    maximum_processing_seconds: float = Field(default=30, gt=0, le=600)

    @model_validator(mode="after")
    def validate_sizes(self) -> "ChunkQualityConfig":
        if self.minimum_chunk_tokens > self.target_chunk_tokens:
            raise ValueError("minimum_chunk_tokens cannot exceed target")
        if self.target_chunk_tokens > self.maximum_chunk_tokens:
            raise ValueError("target_chunk_tokens cannot exceed maximum")
        return self


class ChunkQualityScore(BaseModel):
    overall: float = Field(ge=0, le=100)
    size_quality: float = Field(ge=0, le=100)
    structural_integrity: float = Field(ge=0, le=100)
    information_density: float = Field(ge=0, le=100)
    overlap_efficiency: float = Field(ge=0, le=100)
    source_mapping_quality: float = Field(ge=0, le=100)
    extraction_quality: float = Field(ge=0, le=100)
    explanation: list[str] = Field(default_factory=list)


class ChunkQualityStatistics(BaseModel):
    total_chunks: int = Field(ge=0)
    oversized_chunks: int = Field(ge=0)
    undersized_chunks: int = Field(ge=0)
    empty_chunks: int = Field(ge=0)
    structurally_broken_chunks: int = Field(ge=0)
    average_chunk_tokens: float = Field(ge=0)
    median_chunk_tokens: float = Field(ge=0)
    estimated_redundant_tokens: int = Field(ge=0)


class ChunkQualityResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    scores: dict[str, ChunkQualityScore] = Field(default_factory=dict)
    warnings: list[QualityWarning] = Field(default_factory=list)
    skipped_chunk_ids: list[str] = Field(default_factory=list)
    statistics: ChunkQualityStatistics
    scanner_name: str = Field(min_length=1)
    scanner_version: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
