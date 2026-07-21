"""Unified fully offline static scan orchestration."""

import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ragscanner.chunking import DocumentChunker
from ragscanner.connectors import FilesystemSourceConfig, LocalFilesystemConnector
from ragscanner.domain import (
    Chunk,
    Document,
    Finding,
    Scan,
    ScanStatus,
    ScanType,
    ScoreSummary,
    Severity,
    SourceConnector,
    SourceCursor,
    SourceDescriptor,
    SourceError,
    SourceHealth,
    SourceHealthStatus,
    SourceItem,
)
from ragscanner.normalization import DocumentNormalizer, NormalizationResult
from ragscanner.parsers import ParserResult, ParserWarning, PdfParserError
from ragscanner.pipeline.models import (
    AssessmentCoverage,
    AssessmentStatus,
    SkippedItem,
    StageError,
    StageName,
    StaticPipelineConfig,
    StaticPipelineResult,
    StaticScanEvent,
    StaticScanEventType,
)
from ragscanner.pipeline.registry import ParserRegistry
from ragscanner.quality import (
    ChunkQualityResult,
    ChunkQualityScanner,
    ConsistencyScanner,
    ConsistencyScanResult,
    DuplicateGroup,
    DuplicateScanResult,
    ExactDuplicateScanner,
    NearDuplicateScanner,
)
from ragscanner.quality.models import ChunkQualityStatistics
from ragscanner.security import StaticRuleLibrary, StaticScanResult, StaticSecurityScanner
from ragscanner.security.static_models import StaticScanStatistics
from ragscanner.version import __version__


@runtime_checkable
class StaticScanEventSink(Protocol):
    async def emit(self, event: StaticScanEvent) -> None: ...


class NoOpStaticScanEventSink:
    async def emit(self, event: StaticScanEvent) -> None:
        return None


class TerminalStaticScanEventSink:
    def __init__(self, writer: Callable[[str], None], *, verbose: bool = False) -> None:
        self._writer = writer
        self._verbose = verbose

    async def emit(self, event: StaticScanEvent) -> None:
        always = {
            StaticScanEventType.SCAN_STARTED,
            StaticScanEventType.SCAN_WARNING,
            StaticScanEventType.SCAN_FAILED,
            StaticScanEventType.SCAN_CANCELLED,
            StaticScanEventType.SCAN_COMPLETED,
        }
        if self._verbose or event.event_type in always:
            location = f" [{event.relative_path}]" if event.relative_path else ""
            message = f": {event.message}" if event.message else ""
            self._writer(f"{event.event_type.value}{location}{message}")


class StaticScanPipeline:
    def __init__(
        self,
        config: StaticPipelineConfig,
        *,
        connector: SourceConnector | None = None,
        registry: ParserRegistry | None = None,
        event_sink: StaticScanEventSink | None = None,
        clock: Callable[[], datetime] | None = None,
        single_source: bool | None = None,
    ) -> None:
        self.config = config
        self._single_source = (
            config.source_path.is_file() if single_source is None else single_source
        )
        source_root = config.source_path.parent if self._single_source else config.source_path
        include_patterns = (
            [config.source_path.name] if self._single_source else config.include_patterns
        )
        allowed_extensions = (
            {config.source_path.suffix.casefold()}
            if self._single_source
            else config.allowed_extensions
        )
        self._connector = connector or LocalFilesystemConnector(
            FilesystemSourceConfig(
                root_path=source_root,
                recursive=config.recursive,
                include_patterns=include_patterns,
                exclude_patterns=config.exclude_patterns,
                maximum_file_size=config.maximum_file_size,
                maximum_discovered_files=2
                if self._single_source
                else config.maximum_discovered_files,
                allowed_extensions=allowed_extensions,
            )
        )
        self._registry = registry or ParserRegistry.defaults(
            pdf_config=config.pdf, docx_config=config.docx
        )
        self._sink = event_sink or NoOpStaticScanEventSink()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def report_started(self, scan_id: str) -> None:
        asyncio.run(self._emit(StaticScanEventType.REPORT_STARTED, scan_id))

    def report_completed(self, scan_id: str) -> None:
        asyncio.run(self._emit(StaticScanEventType.REPORT_COMPLETED, scan_id))

    async def run(self) -> StaticPipelineResult:
        started = self._now()
        scan_id = self._scan_id()
        scan = Scan(
            id=scan_id,
            scan_type=ScanType.STATIC,
            source_type="filesystem",
            source_name=self.config.source_path.name,
            status=ScanStatus.RUNNING,
            started_at=started,
            scanner_version=__version__,
            metadata={
                "knowledge_base_mode": "single_source" if self._single_source else "collection"
            },
        )
        await self._emit(StaticScanEventType.SCAN_STARTED, scan_id)
        errors: list[StageError] = []
        skipped: list[SkippedItem] = []
        parser_warnings: dict[str, list[ParserWarning]] = {}
        normalization_warnings: dict[str, list[str]] = {}
        chunking_warnings: dict[str, list[str]] = {}
        documents: list[Document] = []
        chunks: list[Chunk] = []
        normalized_results: dict[str, NormalizationResult] = {}
        parser_results: dict[str, ParserResult] = {}
        descriptor: SourceDescriptor | None = None
        health: SourceHealth | None = None
        try:
            descriptor = await self._connector.describe()
            scan.source_type = descriptor.source_type
            if descriptor.source_type != "filesystem":
                scan.source_name = descriptor.display_name
            health = await self._connector.health_check()
            await self._emit(
                StaticScanEventType.SOURCE_HEALTH_CHECKED,
                scan_id,
                message=health.status.value,
            )
            if health.status is SourceHealthStatus.UNAVAILABLE:
                raise RuntimeError(health.message or "source unavailable")
            await self._emit(StaticScanEventType.DISCOVERY_STARTED, scan_id)
            items = await self._discover(scan_id, skipped)
            scan.files_discovered = len(items)
        except (SourceError, OSError, RuntimeError, ValueError) as error:
            errors.append(
                self._stage_error(StageName.SOURCE, "source_unavailable", error, fatal=True)
            )
            return await self._finalize(
                scan,
                descriptor,
                health,
                documents,
                chunks,
                [],
                [],
                None,
                None,
                parser_warnings,
                normalization_warnings,
                chunking_warnings,
                skipped,
                errors,
                started,
                cancelled=False,
            )

        for item in items:
            if self._cancelled:
                break
            relative = item.path or item.name
            await self._emit(StaticScanEventType.ITEM_DISCOVERED, scan_id, item.id, relative)
            if item.size_bytes is not None and item.size_bytes > self.config.maximum_file_size:
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.RETRIEVAL,
                        reason="file size exceeded",
                    )
                )
                await self._emit(
                    StaticScanEventType.ITEM_SKIPPED,
                    scan_id,
                    item.id,
                    relative,
                    "file size exceeded",
                )
                continue
            try:
                content = await self._connector.get_content(item.id, self.config.maximum_file_size)
                await self._emit(StaticScanEventType.CONTENT_RETRIEVED, scan_id, item.id, relative)
            except (SourceError, OSError, ValueError) as error:
                errors.append(
                    self._stage_error(
                        StageName.RETRIEVAL, "source_read_failed", error, item.id, relative
                    )
                )
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.RETRIEVAL,
                        reason="source read failed",
                    )
                )
                continue
            parser = self._registry.select(content_type=content.content_type, path=item.path)
            if parser is None:
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.PARSING,
                        reason="unsupported file",
                    )
                )
                await self._emit(
                    StaticScanEventType.ITEM_SKIPPED, scan_id, item.id, relative, "unsupported file"
                )
                continue
            try:
                await self._emit(StaticScanEventType.PARSING_STARTED, scan_id, item.id, relative)
                parsed = parser.parse(content)
                parser_results[parsed.document.id] = parsed
                parser_warnings[parsed.document.id] = list(parsed.warnings)
                documents.append(parsed.document)
                await self._emit(StaticScanEventType.PARSING_COMPLETED, scan_id, item.id, relative)
            except Exception as error:  # parser libraries expose distinct safe exception types
                code = "parse_failed"
                reason = "parse failed"
                metadata: dict[str, object] = {}
                if isinstance(error, PdfParserError):
                    code = f"pdf_{error.category.value}"
                    reason = str(error)
                    metadata = {
                        "parser": "pdf",
                        "category": error.category.value,
                        "remediation": error.remediation,
                    }
                errors.append(
                    self._stage_error(
                        StageName.PARSING,
                        code,
                        error,
                        item.id,
                        relative,
                        metadata=metadata,
                    )
                )
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.PARSING,
                        reason=reason,
                    )
                )
                continue
            try:
                normalized = DocumentNormalizer(self.config.normalization).normalize(
                    parsed.document
                )
                normalized_results[parsed.document.id] = normalized
                normalization_warnings[parsed.document.id] = [
                    warning.message for warning in normalized.warnings
                ]
                await self._emit(
                    StaticScanEventType.NORMALIZATION_COMPLETED, scan_id, item.id, relative
                )
            except Exception as error:
                documents.pop()
                parser_results.pop(parsed.document.id, None)
                errors.append(
                    self._stage_error(
                        StageName.NORMALIZATION, "normalization_failed", error, item.id, relative
                    )
                )
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.NORMALIZATION,
                        reason="normalization failed",
                    )
                )
                continue
            try:
                chunked = DocumentChunker(self.config.chunking).chunk(parsed.document, normalized)
                chunks.extend(chunked.chunks)
                chunking_warnings[parsed.document.id] = [
                    warning.message for warning in chunked.warnings
                ]
                await self._emit(StaticScanEventType.CHUNKING_COMPLETED, scan_id, item.id, relative)
            except Exception as error:
                documents.pop()
                normalized_results.pop(parsed.document.id, None)
                parser_results.pop(parsed.document.id, None)
                errors.append(
                    self._stage_error(
                        StageName.CHUNKING, "chunking_failed", error, item.id, relative
                    )
                )
                skipped.append(
                    SkippedItem(
                        item_id=item.id,
                        relative_path=relative,
                        stage=StageName.CHUNKING,
                        reason="chunking failed",
                    )
                )

        scan.files_scanned = len(documents)
        scan.files_skipped = len(skipped)
        scan.chunks_scanned = len(chunks)
        if self._cancelled:
            return await self._finalize(
                scan,
                descriptor,
                health,
                documents,
                chunks,
                [],
                [],
                None,
                None,
                parser_warnings,
                normalization_warnings,
                chunking_warnings,
                skipped,
                errors,
                started,
                cancelled=True,
            )
        if not documents:
            errors.append(
                StageError(
                    stage=StageName.PARSING,
                    code="no_documents_processed",
                    message="No document completed the ingestion pipeline.",
                    fatal=True,
                )
            )

        findings: list[Finding] = []
        duplicate_groups: list[DuplicateGroup] = []
        security_stats: StaticScanStatistics | None = None
        quality_stats: ChunkQualityStatistics | None = None
        exact_result: DuplicateScanResult | None = None
        near_result: DuplicateScanResult | None = None
        quality_result: ChunkQualityResult | None = None
        consistency_result: ConsistencyScanResult | None = None
        if documents and self.config.security_enabled:
            try:
                await self._emit(StaticScanEventType.SECURITY_SCAN_STARTED, scan_id)
                packaged_rules = Path(__file__).resolve().parents[1] / "rules" / "static"
                rule_path = (
                    packaged_rules
                    if packaged_rules.is_dir()
                    else Path(__file__).resolve().parents[5] / "rules" / "static"
                )
                scanner = StaticSecurityScanner(
                    StaticRuleLibrary.from_directory(rule_path), self.config.security
                )
                security_results = [
                    scanner.scan(
                        document,
                        normalized=normalized_results[document.id],
                        chunks=[chunk for chunk in chunks if chunk.document_id == document.id],
                        parser_warnings=parser_results[document.id].warnings,
                    )
                    for document in documents
                ]
                findings.extend(item for result in security_results for item in result.findings)
                security_stats = self._security_statistics(security_results)
                scan.rule_pack_version = (
                    ",".join(
                        sorted(
                            {
                                version
                                for result in security_results
                                for version in result.rule_pack_versions
                            }
                        )
                    )
                    or None
                )
                await self._emit(StaticScanEventType.SECURITY_SCAN_COMPLETED, scan_id)
            except Exception as error:
                errors.append(
                    self._stage_error(StageName.SECURITY, "security_scanner_failed", error)
                )
        if documents and self.config.exact_duplicates_enabled:
            try:
                exact_result = ExactDuplicateScanner(self.config.exact_duplicates).scan(
                    documents, normalized_results, chunks
                )
                findings.extend(exact_result.findings)
                duplicate_groups.extend(exact_result.groups)
            except Exception as error:
                errors.append(
                    self._stage_error(StageName.DUPLICATES, "exact_duplicate_scanner_failed", error)
                )
        if documents and self.config.near_duplicates_enabled:
            try:
                near_result = NearDuplicateScanner(self.config.near_duplicates).scan(
                    documents, normalized_results, chunks
                )
                findings.extend(near_result.findings)
                duplicate_groups.extend(near_result.groups)
            except Exception as error:
                errors.append(
                    self._stage_error(StageName.DUPLICATES, "near_duplicate_scanner_failed", error)
                )
        if documents:
            await self._emit(StaticScanEventType.DUPLICATE_SCAN_COMPLETED, scan_id)
        if documents and self.config.chunk_quality_enabled:
            try:
                quality_result = ChunkQualityScanner(self.config.chunk_quality).scan(
                    documents, chunks, normalized_results
                )
                findings.extend(quality_result.findings)
                quality_stats = quality_result.statistics
                await self._emit(StaticScanEventType.QUALITY_SCAN_COMPLETED, scan_id)
            except Exception as error:
                errors.append(self._stage_error(StageName.QUALITY, "quality_scanner_failed", error))
        if documents and self.config.consistency_enabled:
            try:
                consistency_result = ConsistencyScanner().scan(documents)
                findings.extend(consistency_result.findings)
            except Exception as error:
                errors.append(
                    self._stage_error(StageName.QUALITY, "consistency_scanner_failed", error)
                )
        scores = self._scores(
            findings,
            quality_result,
            exact_result,
            near_result,
            security_assessed=security_stats is not None,
            consistency_assessed=consistency_result is not None,
            document_count=len(documents),
        )
        await self._emit(StaticScanEventType.SCORING_COMPLETED, scan_id)
        return await self._finalize(
            scan,
            descriptor,
            health,
            documents,
            chunks,
            findings,
            duplicate_groups,
            quality_stats,
            security_stats,
            parser_warnings,
            normalization_warnings,
            chunking_warnings,
            skipped,
            errors,
            started,
            cancelled=False,
            scores=scores,
            consistency_result=consistency_result,
        )

    async def _discover(self, scan_id: str, skipped: list[SkippedItem]) -> list[SourceItem]:
        items: list[SourceItem] = []
        cursor: SourceCursor | None = None
        while True:
            if self._cancelled:
                break
            page = await self._connector.list_items(
                cursor, min(500, self.config.maximum_discovered_files)
            )
            items.extend(page.items)
            for warning in page.warnings:
                skipped.append(
                    SkippedItem(
                        item_id=warning.item_id or "source",
                        stage=StageName.DISCOVERY,
                        reason=warning.message,
                    )
                )
                await self._emit(
                    StaticScanEventType.SCAN_WARNING,
                    scan_id,
                    warning.item_id,
                    message=warning.message,
                )
            if not page.has_more or len(items) >= self.config.maximum_discovered_files:
                break
            cursor = page.next_cursor
        return sorted(
            items[: self.config.maximum_discovered_files],
            key=lambda item: (item.path or item.name, item.id),
        )

    async def _finalize(
        self,
        scan: Scan,
        descriptor: SourceDescriptor | None,
        health: SourceHealth | None,
        documents: list[Document],
        chunks: list[Chunk],
        findings: list[Finding],
        duplicate_groups: list[DuplicateGroup],
        quality_stats: ChunkQualityStatistics | None,
        security_stats: StaticScanStatistics | None,
        parser_warnings: dict[str, list[ParserWarning]],
        normalization_warnings: dict[str, list[str]],
        chunking_warnings: dict[str, list[str]],
        skipped: list[SkippedItem],
        errors: list[StageError],
        started: datetime,
        cancelled: bool,
        scores: ScoreSummary | None = None,
        consistency_result: ConsistencyScanResult | None = None,
    ) -> StaticPipelineResult:
        completed = self._now()
        if cancelled:
            status = ScanStatus.CANCELLED
        elif any(error.fatal for error in errors) or not documents:
            status = ScanStatus.FAILED
        elif (
            errors
            or skipped
            or any(parser_warnings.values())
            or any(normalization_warnings.values())
            or any(
                message != "Token counts use a deterministic model-independent approximation."
                for values in chunking_warnings.values()
                for message in values
            )
        ):
            status = ScanStatus.COMPLETED_WITH_WARNINGS
        else:
            status = ScanStatus.COMPLETED
        scan.status = status
        scan.completed_at = completed
        scan.finding_counts = {
            severity.value: sum(item.severity is severity for item in findings)
            for severity in Severity
        }
        scan.warnings = sorted({item.reason for item in skipped})
        scan.errors = sorted({error.message for error in errors})
        event = (
            StaticScanEventType.SCAN_CANCELLED
            if cancelled
            else (
                StaticScanEventType.SCAN_FAILED
                if status is ScanStatus.FAILED
                else StaticScanEventType.SCAN_COMPLETED
            )
        )
        await self._emit(event, scan.id, message=status.value)
        return StaticPipelineResult(
            scan=scan,
            source_descriptor=descriptor,
            source_health=health,
            documents=documents,
            chunks=chunks,
            findings=sorted(findings, key=lambda item: item.fingerprint),
            duplicate_groups=sorted(duplicate_groups, key=lambda item: (item.category, item.id)),
            quality_statistics=quality_stats,
            consistency_result=consistency_result,
            security_statistics=security_stats,
            score_summary=scores or ScoreSummary(),
            parser_warnings=parser_warnings,
            normalization_warnings=normalization_warnings,
            chunking_warnings=chunking_warnings,
            skipped_items=sorted(
                skipped, key=lambda item: (item.relative_path or "", item.item_id)
            ),
            errors=errors,
            started_at=started,
            completed_at=completed,
            cancelled=cancelled,
            metadata={
                "offline": not bool(descriptor and descriptor.capabilities.remote),
                "network_calls": bool(descriptor and descriptor.capabilities.remote),
                "external_ai": False,
            },
            knowledge_base_mode="single_source" if self._single_source else "collection",
            assessment_coverage=self._assessment_coverage(
                documents=documents,
                chunks=chunks,
                security_stats=security_stats,
                quality_stats=quality_stats,
                consistency_result=consistency_result,
                errors=errors,
            ),
        )

    def _assessment_coverage(
        self,
        *,
        documents: list[Document],
        chunks: list[Chunk],
        security_stats: StaticScanStatistics | None,
        quality_stats: ChunkQualityStatistics | None,
        consistency_result: ConsistencyScanResult | None,
        errors: list[StageError],
    ) -> dict[str, AssessmentCoverage]:
        single = self._single_source or len(documents) == 1
        collection_reason = (
            "Requires at least two source documents; this is a single-source knowledge base."
        )
        unavailable_reason = "The corresponding scanner is not implemented in this release."
        duplicate_failed = any(error.stage is StageName.DUPLICATES for error in errors)
        exact_assessed = self.config.exact_duplicates_enabled and not duplicate_failed
        near_assessed = self.config.near_duplicates_enabled and not duplicate_failed
        coverage = {
            "static_security": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if security_stats is not None
                else AssessmentStatus.NOT_ASSESSED,
                reason="Static document and chunk rules were evaluated."
                if security_stats is not None
                else "Static security scanning was disabled or unavailable.",
            ),
            "chunk_quality": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if quality_stats is not None
                else AssessmentStatus.NOT_ASSESSED,
                reason="Chunk-quality heuristics were evaluated."
                if quality_stats is not None
                else "Chunk-quality scanning was disabled or unavailable.",
            ),
            "consistency": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if consistency_result is not None
                else AssessmentStatus.NOT_ASSESSED,
                reason=(
                    "Repeated labelled facts were compared for conflicting values."
                    if consistency_result is not None
                    else "Consistency scanning was disabled or unavailable."
                ),
                metadata={
                    "facts_compared": consistency_result.facts_compared,
                    "conflicting_keys": consistency_result.conflicting_keys,
                }
                if consistency_result is not None
                else {},
            ),
            "within_document_repeated_chunks": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if exact_assessed
                else AssessmentStatus.NOT_ASSESSED,
                reason="Repeated chunks inside the source were evaluated."
                if exact_assessed
                else "Exact duplicate scanning was disabled or failed.",
                metadata={"chunks_available": len(chunks)},
            ),
            "within_document_near_duplicates": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if near_assessed
                else AssessmentStatus.NOT_ASSESSED,
                reason="Lexical near-duplicate chunks inside the source were evaluated."
                if near_assessed
                else "Near-duplicate scanning was disabled or failed.",
                metadata={"chunks_available": len(chunks)},
            ),
            "cross_document_exact_duplicates": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if not single and exact_assessed
                else AssessmentStatus.NOT_ASSESSED,
                reason=collection_reason
                if single
                else (
                    "Normalized content was compared across source documents."
                    if exact_assessed
                    else "Exact duplicate scanning was disabled or failed."
                ),
            ),
            "cross_document_near_duplicates": AssessmentCoverage(
                status=AssessmentStatus.ASSESSED
                if not single and near_assessed
                else AssessmentStatus.NOT_ASSESSED,
                reason=collection_reason
                if single
                else (
                    "Lexical similarity was compared across source documents."
                    if near_assessed
                    else "Near-duplicate scanning was disabled or failed."
                ),
            ),
            "version_conflict": AssessmentCoverage(
                status=AssessmentStatus.PARTIAL
                if consistency_result is not None
                else AssessmentStatus.NOT_ASSESSED,
                reason=(
                    "Explicit repeated labels were checked; semantic contradictions and superseded-version inference remain out of scope."
                    if consistency_result is not None
                    else (collection_reason if single else unavailable_reason)
                ),
            ),
            "cross_document_freshness": AssessmentCoverage(
                status=AssessmentStatus.NOT_ASSESSED,
                reason=collection_reason if single else unavailable_reason,
            ),
        }
        return coverage

    @staticmethod
    def _security_statistics(results: list[StaticScanResult]) -> StaticScanStatistics:
        return StaticScanStatistics(
            rules_evaluated=sum(item.statistics.rules_evaluated for item in results),
            rules_skipped=sum(item.statistics.rules_skipped for item in results),
            matches_evaluated=sum(item.statistics.matches_evaluated for item in results),
            findings_created=sum(item.statistics.findings_created for item in results),
            chunks_scanned=sum(item.statistics.chunks_scanned for item in results),
            metadata_fields_scanned=sum(
                item.statistics.metadata_fields_scanned for item in results
            ),
            decoded_payloads_inspected=sum(
                item.statistics.decoded_payloads_inspected for item in results
            ),
        )

    @staticmethod
    def _scores(
        findings: list[Finding],
        quality_result: ChunkQualityResult | None,
        exact_result: DuplicateScanResult | None,
        near_result: DuplicateScanResult | None,
        *,
        security_assessed: bool,
        consistency_assessed: bool,
        document_count: int,
    ) -> ScoreSummary:
        penalties = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 8,
            Severity.LOW: 3,
            Severity.INFO: 1,
        }
        security_findings = [item for item in findings if item.scanner == "static_security_scanner"]
        security = None
        if security_assessed:
            security = max(
                0.0,
                100.0
                - sum(penalties[item.severity] * item.confidence for item in security_findings),
            )
        consistency_findings = [item for item in findings if item.scanner == "consistency_scanner"]
        consistency = None
        if consistency_assessed:
            consistency = max(
                0.0,
                100.0
                - sum(penalties[item.severity] * item.confidence for item in consistency_findings)
                / max(1, document_count),
            )
        knowledge: float | None = None
        if quality_result is not None and quality_result.scores:
            knowledge = sum(item.overall for item in quality_result.scores.values()) / len(
                quality_result.scores
            )
        percentages = [
            item.statistics.duplicate_content_percentage
            for item in (exact_result, near_result)
            if item is not None
        ]
        efficiency = max(0.0, 100.0 - max(percentages)) if percentages else None
        dimensions = {
            "security": (
                security,
                0.35 + min(0.15, len(security_findings) / max(1, document_count) * 0.03),
            ),
            "consistency": (
                consistency,
                0.30 + min(0.15, len(consistency_findings) / max(1, document_count) * 0.05),
            ),
            "knowledge": (knowledge, 0.20),
            "efficiency": (efficiency, 0.15),
        }
        assessed = [(value, weight) for value, weight in dimensions.values() if value is not None]
        overall = (
            sum(value * weight for value, weight in assessed)
            / sum(weight for _value, weight in assessed)
            if assessed
            else None
        )
        return ScoreSummary(
            overall=overall,
            knowledge_quality=knowledge,
            consistency=consistency,
            security=security,
            efficiency=efficiency,
        )

    def _scan_id(self) -> str:
        payload = self.config.model_dump(
            mode="json", exclude={"output_path", "output_format", "progress_mode"}
        )
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(f"static-scan:v1:{canonical}".encode()).hexdigest()

    def _stage_error(
        self,
        stage: StageName,
        code: str,
        error: BaseException,
        item_id: str | None = None,
        relative: str | None = None,
        fatal: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> StageError:
        safe_message = str(error).replace(str(self.config.source_path), "<source-root>")[:1024]
        return StageError(
            stage=stage,
            code=code,
            message=safe_message,
            item_id=item_id,
            relative_path=relative,
            fatal=fatal,
            metadata=metadata or {},
        )

    async def _emit(
        self,
        event_type: StaticScanEventType,
        scan_id: str,
        item_id: str | None = None,
        relative_path: str | None = None,
        message: str | None = None,
    ) -> None:
        try:
            await self._sink.emit(
                StaticScanEvent(
                    event_type=event_type,
                    scan_id=scan_id,
                    occurred_at=self._now(),
                    item_id=item_id,
                    relative_path=relative_path,
                    message=message,
                )
            )
        except Exception:
            return

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("pipeline clock must return timezone-aware datetimes")
        return value


def run_static_pipeline(pipeline: StaticScanPipeline) -> StaticPipelineResult:
    return asyncio.run(pipeline.run())
