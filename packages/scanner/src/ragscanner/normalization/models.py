"""Framework-independent document normalization contracts."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ragscanner.domain import SourceLocation


class UnicodeForm(StrEnum):
    NFC = "NFC"
    NFKC = "NFKC"
    NONE = "none"


class AnnotationType(StrEnum):
    BOILERPLATE_CANDIDATE = "boilerplate_candidate"
    HEADER_CANDIDATE = "header_candidate"
    FOOTER_CANDIDATE = "footer_candidate"
    PAGE_NUMBER_CANDIDATE = "page_number_candidate"
    INVISIBLE_UNICODE = "invisible_unicode"
    BIDI_CONTROL = "bidi_control"
    REPLACEMENT_CHARACTER = "replacement_character"
    GARBLED_TEXT = "garbled_text"
    CODE_REGION = "code_region"
    TABLE_REGION = "table_region"
    LIST_REGION = "list_region"
    HEADING_REGION = "heading_region"
    PAGE_BOUNDARY = "page_boundary"
    SECTION_BOUNDARY = "section_boundary"
    HEADER_REGION = "header_region"
    FOOTER_REGION = "footer_region"


class NormalizationWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    original_start: int | None = Field(default=None, ge=0)
    original_end: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizationAnnotation(BaseModel):
    annotation_type: AnnotationType
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=0)
    original_start: int | None = Field(default=None, ge=0)
    original_end: int | None = Field(default=None, ge=0)
    normalized_text: str | None = None
    occurrence_count: int = Field(default=1, ge=1)
    pages: list[int] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0, le=1)
    candidate_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizationSegment(BaseModel):
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=0)
    original_start: int = Field(ge=0)
    original_end: int = Field(ge=0)
    source_location: SourceLocation
    transformation_types: list[str] = Field(default_factory=list)
    approximate: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_ranges(self) -> "NormalizationSegment":
        if self.normalized_end < self.normalized_start:
            raise ValueError("normalized range is reversed")
        if self.original_end < self.original_start:
            raise ValueError("original range is reversed")
        return self


class NormalizationStatistics(BaseModel):
    original_characters: int = Field(ge=0)
    normalized_characters: int = Field(ge=0)
    unicode_changes: int = Field(default=0, ge=0)
    newline_changes: int = Field(default=0, ge=0)
    control_markers: int = Field(default=0, ge=0)
    whitespace_changes: int = Field(default=0, ge=0)
    blank_lines_removed: int = Field(default=0, ge=0)
    soft_hyphens_marked: int = Field(default=0, ge=0)
    pdf_wrap_repairs: int = Field(default=0, ge=0)
    hyphenated_line_repairs: int = Field(default=0, ge=0)
    boilerplate_candidates: int = Field(default=0, ge=0)
    segments: int = Field(default=0, ge=0)
    annotations: int = Field(default=0, ge=0)


class NormalizationConfig(BaseModel):
    unicode_form: UnicodeForm = UnicodeForm.NFC
    normalize_newlines: bool = True
    visible_control_markers: bool = True
    normalize_horizontal_whitespace: bool = True
    trim_lines: bool = True
    maximum_consecutive_blank_lines: int = Field(default=2, ge=0, le=20)
    repair_pdf_wraps: bool = True
    repair_hyphenated_line_breaks: bool = True
    preserve_page_boundaries: bool = True
    detect_boilerplate: bool = True
    annotate_invisible_unicode: bool = True
    maximum_normalization_segments: int = Field(default=100_000, gt=0)
    maximum_annotations: int = Field(default=10_000, gt=0)
    maximum_normalized_output_size: int = Field(default=5_000_000, gt=0)


class NormalizationResult(BaseModel):
    document_id: str = Field(min_length=1)
    original_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized_content: str
    normalized_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    segments: list[NormalizationSegment] = Field(default_factory=list)
    warnings: list[NormalizationWarning] = Field(default_factory=list)
    annotations: list[NormalizationAnnotation] = Field(default_factory=list)
    statistics: NormalizationStatistics
    normalizer_name: str = Field(min_length=1)
    normalizer_version: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizationErrorCategory(StrEnum):
    INVALID_INPUT = "invalid_input"
    OUTPUT_LIMIT_EXCEEDED = "output_limit_exceeded"


class NormalizationError(Exception):
    def __init__(self, category: NormalizationErrorCategory, message: str) -> None:
        self.category = category
        super().__init__(message)
