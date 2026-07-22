"""Framework-independent document chunking contracts."""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator

from ragscanner.domain import Chunk


class ChunkingStrategy(StrEnum):
    STRUCTURE_AWARE = "structure_aware"
    PARAGRAPH_AWARE = "paragraph_aware"
    TOKEN_WINDOW = "token_window"  # noqa: S105 - strategy name, not a credential


class TokenizerStrategy(StrEnum):
    WHITESPACE_APPROXIMATION = "whitespace_approximation"


class ChunkingConfig(BaseModel):
    strategy: ChunkingStrategy = ChunkingStrategy.STRUCTURE_AWARE
    target_token_count: int = Field(default=300, gt=0)
    maximum_token_count: int = Field(default=500, gt=0)
    minimum_token_count: int = Field(default=50, ge=0)
    overlap_token_count: int = Field(default=30, ge=0)
    maximum_characters: int = Field(default=100_000, gt=0)
    tokenizer_strategy: TokenizerStrategy = TokenizerStrategy.WHITESPACE_APPROXIMATION
    preserve_page_boundaries: bool = True
    preserve_tables: bool = True
    preserve_code_blocks: bool = True
    attach_heading_context: bool = True
    merge_small_adjacent_sections: bool = True
    maximum_input_characters: int = Field(default=5_000_000, gt=0)
    maximum_blocks: int = Field(default=100_000, gt=0)
    maximum_chunks_per_document: int = Field(default=10_000, gt=0)
    maximum_overlap_tokens: int = Field(default=100, ge=0)
    maximum_overlap_ratio: float = Field(default=0.2, ge=0, le=0.5)
    maximum_metadata_characters: int = Field(default=16_384, gt=0)

    @model_validator(mode="after")
    def validate_sizes(self) -> "ChunkingConfig":
        if self.target_token_count > self.maximum_token_count:
            raise ValueError("target_token_count cannot exceed maximum_token_count")
        if self.minimum_token_count > self.maximum_token_count:
            raise ValueError("minimum_token_count cannot exceed maximum_token_count")
        if self.overlap_token_count > self.maximum_overlap_tokens:
            raise ValueError("overlap_token_count exceeds maximum_overlap_tokens")
        if self.overlap_token_count >= self.maximum_token_count:
            raise ValueError("overlap must be smaller than maximum_token_count")
        return self


class TokenSpan(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


@runtime_checkable
class TokenCounter(Protocol):
    name: str
    version: str

    def spans(self, text: str) -> list[TokenSpan]: ...

    def count(self, text: str) -> int: ...


class ChunkingWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    normalized_start: int | None = Field(default=None, ge=0)
    normalized_end: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkingStatistics(BaseModel):
    input_characters: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    blocks: int = Field(ge=0)
    chunks: int = Field(ge=0)
    forced_splits: int = Field(default=0, ge=0)
    overlap_tokens: int = Field(default=0, ge=0)
    approximate_mappings: int = Field(default=0, ge=0)


class ChunkingResult(BaseModel):
    document_id: str = Field(min_length=1)
    normalized_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    chunks: list[Chunk] = Field(default_factory=list)
    warnings: list[ChunkingWarning] = Field(default_factory=list)
    statistics: ChunkingStatistics
    chunker_name: str = Field(min_length=1)
    chunker_version: str = Field(min_length=1)
    tokenizer_name: str = Field(min_length=1)
    tokenizer_version: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkingErrorCategory(StrEnum):
    INVALID_INPUT = "invalid_input"
    INPUT_LIMIT_EXCEEDED = "input_limit_exceeded"
    BLOCK_LIMIT_EXCEEDED = "block_limit_exceeded"
    MAXIMUM_CHUNKS_REACHED = "maximum_chunks_reached"


class ChunkingError(Exception):
    def __init__(self, category: ChunkingErrorCategory, message: str) -> None:
        self.category = category
        super().__init__(message)
