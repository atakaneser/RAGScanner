"""Typed unified static scan configuration, result, error, and progress contracts."""

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from ragscanner.chunking import ChunkingConfig
from ragscanner.domain import (
    Chunk,
    Document,
    Finding,
    Scan,
    ScoreSummary,
    Severity,
    SourceDescriptor,
    SourceHealth,
)
from ragscanner.normalization import NormalizationConfig
from ragscanner.parsers import DocxParserConfig, ParserWarning, PdfParserConfig
from ragscanner.pipeline.registry import DEFAULT_DOCUMENT_PATTERNS, SUPPORTED_DOCUMENT_EXTENSIONS
from ragscanner.quality import (
    ChunkQualityConfig,
    DuplicateGroup,
    DuplicateScanConfig,
    NearDuplicateConfig,
)
from ragscanner.quality.models import ChunkQualityStatistics
from ragscanner.security import StaticScanConfig
from ragscanner.security.static_models import StaticScanStatistics


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"
    HTML = "html"


class ProgressMode(StrEnum):
    NORMAL = "normal"
    QUIET = "quiet"
    VERBOSE = "verbose"


class StageName(StrEnum):
    SOURCE = "source"
    DISCOVERY = "discovery"
    RETRIEVAL = "retrieval"
    PARSING = "parsing"
    NORMALIZATION = "normalization"
    CHUNKING = "chunking"
    SECURITY = "security"
    DUPLICATES = "duplicates"
    QUALITY = "quality"
    SCORING = "scoring"
    REPORTING = "reporting"


class AssessmentStatus(StrEnum):
    ASSESSED = "assessed"
    NOT_ASSESSED = "not_assessed"
    PARTIAL = "partial"
    FAILED = "failed"


class AssessmentCoverage(BaseModel):
    status: AssessmentStatus
    reason: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageError(BaseModel):
    stage: StageName
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    item_id: str | None = None
    relative_path: str | None = None
    fatal: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkippedItem(BaseModel):
    item_id: str
    relative_path: str | None = None
    stage: StageName
    reason: str


class StaticPipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_path: Path
    recursive: bool = True
    include_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_DOCUMENT_PATTERNS))
    exclude_patterns: list[str] = Field(default_factory=lambda: [".git/**", "**/.git/**"])
    allowed_extensions: set[str] = Field(default_factory=lambda: set(SUPPORTED_DOCUMENT_EXTENSIONS))
    maximum_file_size: int = Field(default=25 * 1024 * 1024, gt=0)
    maximum_discovered_files: int = Field(default=10_000, gt=0)
    pdf: PdfParserConfig = Field(default_factory=PdfParserConfig)
    docx: DocxParserConfig = Field(default_factory=DocxParserConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    security_enabled: bool = True
    security: StaticScanConfig = Field(default_factory=StaticScanConfig)
    exact_duplicates_enabled: bool = True
    exact_duplicates: DuplicateScanConfig = Field(default_factory=DuplicateScanConfig)
    near_duplicates_enabled: bool = True
    near_duplicates: NearDuplicateConfig = Field(default_factory=NearDuplicateConfig)
    chunk_quality_enabled: bool = True
    chunk_quality: ChunkQualityConfig = Field(default_factory=ChunkQualityConfig)
    output_format: OutputFormat = OutputFormat.TERMINAL
    output_path: Path | None = None
    minimum_severity: Severity | None = None
    fail_on_severity: Severity | None = None
    maximum_findings: int = Field(default=500, gt=0, le=100_000)
    show_relative_paths: bool = True
    progress_mode: ProgressMode = ProgressMode.NORMAL
    allow_output_overwrite: bool = False
    create_output_parents: bool = False
    write_partial_report_on_cancel: bool = False

    @field_validator("allowed_extensions")
    @classmethod
    def normalize_extensions(cls, value: set[str]) -> set[str]:
        supported = SUPPORTED_DOCUMENT_EXTENSIONS
        normalized = {
            item.casefold() if item.startswith(".") else f".{item.casefold()}" for item in value
        }
        if not normalized or not normalized <= supported:
            raise ValueError("allowed_extensions contains unsupported values")
        return normalized

    @model_validator(mode="after")
    def validate_modes(self) -> "StaticPipelineConfig":
        if not self.source_path.is_absolute():
            raise ValueError("source_path must be absolute")
        if not self.security_enabled and not any(
            (
                self.exact_duplicates_enabled,
                self.near_duplicates_enabled,
                self.chunk_quality_enabled,
            )
        ):
            raise ValueError("at least one scanner must be enabled")
        if self.output_format is OutputFormat.HTML and self.output_path is None:
            raise ValueError("HTML output requires output_path")
        return self


class StaticPipelineResult(BaseModel):
    scan: Scan
    source_descriptor: SourceDescriptor | None = None
    source_health: SourceHealth | None = None
    documents: list[Document] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    duplicate_groups: list[DuplicateGroup] = Field(default_factory=list)
    quality_statistics: ChunkQualityStatistics | None = None
    security_statistics: StaticScanStatistics | None = None
    score_summary: ScoreSummary
    parser_warnings: dict[str, list[ParserWarning]] = Field(default_factory=dict)
    normalization_warnings: dict[str, list[str]] = Field(default_factory=dict)
    chunking_warnings: dict[str, list[str]] = Field(default_factory=dict)
    skipped_items: list[SkippedItem] = Field(default_factory=list)
    errors: list[StageError] = Field(default_factory=list)
    started_at: AwareDatetime
    completed_at: AwareDatetime
    cancelled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    knowledge_base_mode: str = "collection"
    assessment_coverage: dict[str, AssessmentCoverage] = Field(default_factory=dict)


class StaticScanEventType(StrEnum):
    SCAN_STARTED = "scan_started"
    SOURCE_HEALTH_CHECKED = "source_health_checked"
    DISCOVERY_STARTED = "discovery_started"
    ITEM_DISCOVERED = "item_discovered"
    ITEM_SKIPPED = "item_skipped"
    CONTENT_RETRIEVED = "content_retrieved"
    PARSING_STARTED = "parsing_started"
    PARSING_COMPLETED = "parsing_completed"
    NORMALIZATION_COMPLETED = "normalization_completed"
    CHUNKING_COMPLETED = "chunking_completed"
    SECURITY_SCAN_STARTED = "security_scan_started"
    SECURITY_SCAN_COMPLETED = "security_scan_completed"
    DUPLICATE_SCAN_COMPLETED = "duplicate_scan_completed"
    QUALITY_SCAN_COMPLETED = "quality_scan_completed"
    SCORING_COMPLETED = "scoring_completed"
    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"
    SCAN_WARNING = "scan_warning"
    SCAN_FAILED = "scan_failed"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_COMPLETED = "scan_completed"


class StaticScanEvent(BaseModel):
    event_type: StaticScanEventType
    scan_id: str
    occurred_at: AwareDatetime
    item_id: str | None = None
    relative_path: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
