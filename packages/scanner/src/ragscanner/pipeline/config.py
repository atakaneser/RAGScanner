"""Strict local TOML configuration loading for the unified static pipeline."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ragscanner.chunking import ChunkingConfig, ChunkingStrategy
from ragscanner.domain import Severity
from ragscanner.normalization import NormalizationConfig
from ragscanner.parsers import DocxParserConfig, PdfParserConfig
from ragscanner.pipeline.models import OutputFormat, StaticPipelineConfig
from ragscanner.pipeline.registry import DEFAULT_DOCUMENT_PATTERNS, SUPPORTED_DOCUMENT_EXTENSIONS
from ragscanner.quality import (
    ChunkQualityConfig,
    NearDuplicateConfig,
    RAGConfigurationConfig,
    RAGProfile,
)
from ragscanner.scoring import ScoringPolicy


class ScanFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recursive: bool = True
    include: list[str] = Field(default_factory=lambda: list(DEFAULT_DOCUMENT_PATTERNS))
    exclude: list[str] = Field(default_factory=lambda: [".git/**", "**/.git/**"])
    allowed_extensions: set[str] = Field(default_factory=lambda: set(SUPPORTED_DOCUMENT_EXTENSIONS))
    max_file_size_mb: float = Field(default=25, gt=0, le=1024)
    max_files: int = Field(default=10_000, gt=0)


class SecurityFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    include_pii: bool = False
    categories: set[str] = Field(default_factory=set)
    exclude_rules: set[str] = Field(default_factory=set)
    minimum_severity: Severity | None = None


class ChunkingFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: ChunkingStrategy = ChunkingStrategy.STRUCTURE_AWARE
    target_tokens: int = Field(default=300, gt=0)
    max_tokens: int = Field(default=500, gt=0)
    min_tokens: int = Field(default=50, ge=0)
    overlap_tokens: int = Field(default=30, ge=0)


class DuplicateFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exact: bool = True
    near: bool = True
    similarity_threshold: float = Field(default=0.82, ge=0.5, le=1)


class QualityFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class RAGFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: RAGProfile = RAGProfile.GENERAL_QA
    embedding_context_tokens: int | None = Field(default=None, ge=128, le=10_000_000)
    generator_context_tokens: int | None = Field(default=None, ge=128, le=10_000_000)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=1_000)


class ScoringFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0.0"
    security_weight: float = Field(default=0.35, ge=0, le=1)
    knowledge_quality_weight: float = Field(default=0.20, ge=0, le=1)
    efficiency_weight: float = Field(default=0.15, ge=0, le=1)
    critical_security_cap: float | None = Field(default=54.99, ge=0, le=100)
    minimum_assessed_dimensions: int = Field(default=2, ge=1, le=3)


class LimitsFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pdf_max_pages: int = Field(default=1_000, gt=0)
    pdf_max_characters: int = Field(default=5_000_000, gt=0)
    docx_max_characters: int = Field(default=5_000_000, gt=0)
    normalized_max_characters: int = Field(default=5_000_000, gt=0)
    max_chunks_per_document: int = Field(default=10_000, gt=0)


class ReportFileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: OutputFormat = OutputFormat.TERMINAL
    output: Path | None = None
    show_relative_paths: bool = True
    max_findings: int = Field(default=500, gt=0)
    overwrite: bool = False
    create_parent_directories: bool = False


class LocalScanFileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan: ScanFileSection = Field(default_factory=ScanFileSection)
    security: SecurityFileSection = Field(default_factory=SecurityFileSection)
    chunking: ChunkingFileSection = Field(default_factory=ChunkingFileSection)
    duplicates: DuplicateFileSection = Field(default_factory=DuplicateFileSection)
    quality: QualityFileSection = Field(default_factory=QualityFileSection)
    rag: RAGFileSection = Field(default_factory=RAGFileSection)
    scoring: ScoringFileSection = Field(default_factory=ScoringFileSection)
    limits: LimitsFileSection = Field(default_factory=LimitsFileSection)
    report: ReportFileSection = Field(default_factory=ReportFileSection)

    def pipeline_config(self, source_path: Path) -> StaticPipelineConfig:
        chunking = ChunkingConfig(
            strategy=self.chunking.strategy,
            target_token_count=self.chunking.target_tokens,
            maximum_token_count=self.chunking.max_tokens,
            minimum_token_count=self.chunking.min_tokens,
            overlap_token_count=self.chunking.overlap_tokens,
        )
        quality_target = min(self.chunking.target_tokens, self.chunking.max_tokens)
        maximum_file_size = int(self.scan.max_file_size_mb * 1024 * 1024)
        config = StaticPipelineConfig(
            source_path=source_path.resolve(),
            recursive=self.scan.recursive,
            include_patterns=self.scan.include,
            exclude_patterns=self.scan.exclude,
            allowed_extensions=self.scan.allowed_extensions,
            maximum_file_size=maximum_file_size,
            maximum_discovered_files=self.scan.max_files,
            security_enabled=self.security.enabled,
            exact_duplicates_enabled=self.duplicates.exact,
            near_duplicates_enabled=self.duplicates.near,
            near_duplicates=NearDuplicateConfig(
                similarity_threshold=self.duplicates.similarity_threshold
            ),
            chunk_quality_enabled=self.quality.enabled,
            chunk_quality=ChunkQualityConfig(
                minimum_chunk_tokens=min(self.chunking.min_tokens, quality_target),
                target_chunk_tokens=quality_target,
                maximum_chunk_tokens=self.chunking.max_tokens,
            ),
            rag=RAGConfigurationConfig(
                profile=self.rag.profile,
                embedding_context_tokens=self.rag.embedding_context_tokens,
                generator_context_tokens=self.rag.generator_context_tokens,
                retrieval_top_k=self.rag.retrieval_top_k,
            ),
            scoring=ScoringPolicy(
                version=self.scoring.version,
                weights={
                    "security": self.scoring.security_weight,
                    "knowledge_quality": self.scoring.knowledge_quality_weight,
                    "efficiency": self.scoring.efficiency_weight,
                },
                critical_security_cap=self.scoring.critical_security_cap,
                minimum_assessed_dimensions=self.scoring.minimum_assessed_dimensions,
            ),
            chunking=chunking,
            pdf=PdfParserConfig(
                maximum_file_size=maximum_file_size,
                maximum_page_count=self.limits.pdf_max_pages,
                maximum_extracted_characters=self.limits.pdf_max_characters,
            ),
            docx=DocxParserConfig(
                maximum_file_size=maximum_file_size,
                maximum_extracted_characters=self.limits.docx_max_characters,
            ),
            normalization=NormalizationConfig(
                maximum_normalized_output_size=self.limits.normalized_max_characters
            ),
            output_format=self.report.format,
            output_path=self.report.output,
            minimum_severity=self.security.minimum_severity,
            maximum_findings=self.report.max_findings,
            show_relative_paths=self.report.show_relative_paths,
            allow_output_overwrite=self.report.overwrite,
            create_output_parents=self.report.create_parent_directories,
        )
        config = config.model_copy(
            update={
                "chunking": config.chunking.model_copy(
                    update={
                        "maximum_input_characters": self.limits.normalized_max_characters,
                        "maximum_chunks_per_document": self.limits.max_chunks_per_document,
                    }
                )
            }
        )
        selection = config.security.selection.model_copy(
            update={
                "categories": self.security.categories,
                "excluded_rule_ids": self.security.exclude_rules,
                "include_pii": self.security.include_pii,
            }
        )
        return config.model_copy(
            update={"security": config.security.model_copy(update={"selection": selection})}
        )


def load_local_scan_config(path: Path | None) -> LocalScanFileConfig:
    if path is None:
        return LocalScanFileConfig()
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot load local TOML config: {error}") from error
    return LocalScanFileConfig.model_validate(payload)
