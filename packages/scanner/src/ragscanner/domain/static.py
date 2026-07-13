"""Static knowledge scanning domain models."""

from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from ragscanner.domain.helpers import document_content_hash


class SourceLocation(BaseModel):
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_path: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_line_range(self) -> "SourceLocation":
        if self.line_start is not None and self.line_end is not None:
            if self.line_end < self.line_start:
                raise ValueError("line_end cannot be before line_start")
        return self


class Document(BaseModel):
    id: str = Field(min_length=1)
    source: SourceLocation
    title: str | None = None
    content: str
    normalized_content: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mime_type: str | None = None
    language: str | None = None
    created_at: AwareDatetime | None = None
    modified_at: AwareDatetime | None = None
    ingested_at: AwareDatetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("content_hash must be SHA-256")
        return value

    def hash_matches_content(self) -> bool:
        return self.content_hash == document_content_hash(self.content)


class Chunk(BaseModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    index: int = Field(ge=0)
    content: str
    normalized_content: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    token_count: int = Field(ge=0)
    character_count: int = Field(ge=0)
    source: SourceLocation
    headings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_character_count(self) -> "Chunk":
        if self.character_count != len(self.content):
            raise ValueError("character_count must match content length")
        return self
