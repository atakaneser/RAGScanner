"""Application service for local static scans and durable scan jobs."""

import asyncio
import os
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.ai_analysis.service import enrich_report
from ragscanner.application.jobs import JobCancellationRequested, JobCheckpoint, JobHandler
from ragscanner.connectors import (
    OpenWebUISourceConfig,
    OpenWebUISourceConnector,
    WebsiteSourceConfig,
    WebsiteSourceConnector,
)
from ragscanner.history import ScanHistoryRepository
from ragscanner.jobs import JobKind, JobRecord
from ragscanner.pipeline import (
    LocalScanFileConfig,
    StaticPipelineConfig,
    StaticPipelineResult,
    StaticScanEvent,
    StaticScanEventSink,
    StaticScanPipeline,
    load_local_scan_config,
    run_static_pipeline,
)
from ragscanner.providers import ModelProviderError, create_analysis_provider
from ragscanner.quality import RAGConfigurationConfig
from ragscanner.reporting import ReportBuilder, ReportFilter, ReportInput, ReportLimits
from ragscanner.reporting.models import ReportDocument
from ragscanner.storage.machine_secrets import resolve_file_secret_reference

AI_HEARTBEAT_SECONDS = 10.0


class StaticScanJobPayload(BaseModel):
    """Bounded scan parameters safe to persist in a job record."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str = Field(default="local", pattern=r"^(local|openwebui|website)$")
    execution_mode: str = Field(default="one_time", pattern=r"^(one_time|scheduled)$")
    source_name: str | None = Field(default=None, min_length=1, max_length=160)
    path: str | None = Field(default=None, min_length=1, max_length=4096)
    config_path: str | None = Field(default=None, min_length=1, max_length=4096)
    openwebui_base_url: str | None = Field(default=None, max_length=2048)
    openwebui_knowledge_id: str | None = Field(default=None, max_length=240)
    website_url: str | None = Field(default=None, max_length=4096)
    credential_ref: str | None = Field(default=None, max_length=500)
    content_consent: bool = False
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig)
    rag: RAGConfigurationConfig | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "StaticScanJobPayload":
        if self.source_kind == "local":
            if self.path is None:
                raise ValueError("local scan jobs require path")
            if any(
                value is not None
                for value in (
                    self.openwebui_base_url,
                    self.openwebui_knowledge_id,
                    self.website_url,
                    self.credential_ref,
                )
            ):
                raise ValueError("local scan jobs cannot include remote source configuration")
        elif self.source_kind == "openwebui" and not all(
            (self.openwebui_base_url, self.openwebui_knowledge_id, self.credential_ref)
        ):
            raise ValueError(
                "OpenWebUI scan jobs require endpoint, knowledge ID, and credential reference"
            )
        elif self.source_kind == "website" and self.website_url is None:
            raise ValueError("website scan jobs require a URL")
        if self.source_kind in {"openwebui", "website"} and not self.content_consent:
            raise ValueError("remote content scans require explicit content consent")
        return self


class _CheckpointEventSink(StaticScanEventSink):
    def __init__(
        self,
        checkpoint: JobCheckpoint,
        pipeline_provider: Callable[[], StaticScanPipeline],
    ) -> None:
        self._checkpoint = checkpoint
        self._pipeline_provider = pipeline_provider
        self.cancellation_requested = False
        self._events = 0

    async def emit(self, _event: StaticScanEvent) -> None:
        self._events += 1
        try:
            self._checkpoint(min(0.75, 0.05 + self._events / 100))
        except JobCancellationRequested:
            self.cancellation_requested = True
            self._pipeline_provider().cancel()


class StaticScanApplicationService:
    """Run a static pipeline and persist its immutable report snapshot."""

    def __init__(self, history_repository: ScanHistoryRepository) -> None:
        self.history_repository = history_repository

    def run_local(
        self,
        source_path: Path,
        *,
        config_path: Path | None = None,
        checkpoint: JobCheckpoint | None = None,
        ai_config: AIProviderConfig | None = None,
        rag_config: RAGConfigurationConfig | None = None,
        source_name: str | None = None,
    ) -> tuple[str, ReportDocument]:
        resolved_source = source_path.expanduser().resolve(strict=True)
        resolved_config = config_path.expanduser().resolve(strict=True) if config_path else None
        config = load_local_scan_config(resolved_config).pipeline_config(resolved_source)
        if rag_config is not None:
            config = config.model_copy(update={"rag": rag_config})
        if (
            resolved_source.is_file()
            and resolved_source.suffix.casefold() not in config.allowed_extensions
        ):
            raise ValueError("single-file scan uses the configured supported document extensions")

        pipeline_holder: dict[str, StaticScanPipeline] = {}
        sink = (
            _CheckpointEventSink(checkpoint, lambda: pipeline_holder["pipeline"])
            if checkpoint is not None
            else None
        )
        pipeline = StaticScanPipeline(config, event_sink=sink)
        pipeline_holder["pipeline"] = pipeline
        result = run_static_pipeline(pipeline)
        report = build_pipeline_report(
            result,
            show_absolute_paths=not config.show_relative_paths,
            maximum_findings=config.maximum_findings,
        )
        if source_name:
            report = report.model_copy(update={"scan": {**report.scan, "source_name": source_name}})
        report = self._enrich_sync(report, ai_config or AIProviderConfig(), checkpoint)
        if checkpoint is not None:
            checkpoint(0.98)
        history_id = self.history_repository.save(report)
        if sink is not None and sink.cancellation_requested:
            raise JobCancellationRequested(f"history:{history_id}")
        return history_id, report

    def run_openwebui(
        self,
        *,
        base_url: str,
        knowledge_id: str,
        credential_ref: str,
        content_consent: bool,
        checkpoint: JobCheckpoint | None = None,
        ai_config: AIProviderConfig | None = None,
        rag_config: RAGConfigurationConfig | None = None,
        source_name: str | None = None,
    ) -> tuple[str, ReportDocument]:
        api_key = resolve_secret_reference(credential_ref)
        connector = OpenWebUISourceConnector(
            OpenWebUISourceConfig(
                base_url=base_url,
                knowledge_id=knowledge_id,
                credential_ref=credential_ref,
                content_consent=content_consent,
            ),
            api_key=api_key,
        )
        config = LocalScanFileConfig().pipeline_config(Path(f"/openwebui/{knowledge_id}"))
        if rag_config is not None:
            config = config.model_copy(update={"rag": rag_config})
        return asyncio.run(
            self._run_connector(
                config,
                connector,
                checkpoint=checkpoint,
                ai_config=ai_config or AIProviderConfig(),
                source_name=source_name,
            )
        )

    def run_website(
        self,
        *,
        url: str,
        credential_ref: str | None,
        content_consent: bool,
        checkpoint: JobCheckpoint | None = None,
        ai_config: AIProviderConfig | None = None,
        rag_config: RAGConfigurationConfig | None = None,
        source_name: str | None = None,
    ) -> tuple[str, ReportDocument]:
        token = resolve_secret_reference(credential_ref) if credential_ref else ""
        connector = WebsiteSourceConnector(
            WebsiteSourceConfig(
                url=url,
                source_name=source_name or "Website",
                credential_ref=credential_ref,
                content_consent=content_consent,
            ),
            bearer_token=token,
        )
        config = LocalScanFileConfig().pipeline_config(Path("/website/content"))
        if rag_config is not None:
            config = config.model_copy(update={"rag": rag_config})
        return asyncio.run(
            self._run_connector(
                config,
                connector,
                checkpoint=checkpoint,
                ai_config=ai_config or AIProviderConfig(),
                source_name=source_name,
            )
        )

    async def _run_connector(
        self,
        config: StaticPipelineConfig,
        connector: OpenWebUISourceConnector | WebsiteSourceConnector,
        *,
        checkpoint: JobCheckpoint | None,
        ai_config: AIProviderConfig,
        source_name: str | None = None,
    ) -> tuple[str, ReportDocument]:
        try:
            pipeline_holder: dict[str, StaticScanPipeline] = {}
            sink = (
                _CheckpointEventSink(checkpoint, lambda: pipeline_holder["pipeline"])
                if checkpoint is not None
                else None
            )
            pipeline = StaticScanPipeline(
                config,
                connector=connector,
                event_sink=sink,
                single_source=False,
            )
            pipeline_holder["pipeline"] = pipeline
            result = await pipeline.run()
            report = build_pipeline_report(
                result,
                show_absolute_paths=False,
                maximum_findings=config.maximum_findings,
            )
            if source_name:
                report = report.model_copy(
                    update={"scan": {**report.scan, "source_name": source_name}}
                )
            report = await self._enrich_async(report, ai_config, checkpoint)
            if checkpoint is not None:
                checkpoint(0.98)
            history_id = self.history_repository.save(report)
            if sink is not None and sink.cancellation_requested:
                raise JobCancellationRequested(f"history:{history_id}")
            return history_id, report
        finally:
            await connector.aclose()

    @staticmethod
    async def _enrich_async(
        report: ReportDocument,
        config: AIProviderConfig,
        checkpoint: JobCheckpoint | None = None,
    ) -> ReportDocument:
        if not config.enabled:
            if checkpoint is not None:
                checkpoint(0.9)
            return report
        if checkpoint is not None:
            checkpoint(0.8)
        try:
            task = asyncio.create_task(
                enrich_report(
                    report,
                    config,
                    provider_factory=lambda selected: create_analysis_provider(
                        selected, secret_resolver=resolve_secret_reference
                    ),
                )
            )
            progress = 0.82
            try:
                while not task.done():
                    done, _pending = await asyncio.wait({task}, timeout=AI_HEARTBEAT_SECONDS)
                    if done:
                        break
                    if checkpoint is not None:
                        checkpoint(progress)
                        progress = min(0.94, progress + 0.02)
                enriched = await task
            finally:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            if checkpoint is not None:
                checkpoint(0.96)
            return enriched
        except ModelProviderError as error:
            failure_code = error.code
            failure_message = error.safe_message
        except ValueError:
            failure_code = (
                "ai_credential_unavailable"
                if config.credential_ref
                else "ai_provider_configuration_invalid"
            )
            failure_message = (
                "The AI credential reference is unavailable to the Host Service."
                if config.credential_ref
                else "The AI provider configuration is invalid."
            )
        except OSError:
            failure_code = "ai_provider_unavailable"
            failure_message = "The AI provider was unavailable."
        if checkpoint is not None:
            checkpoint(0.96)
        return report.model_copy(
            update={
                "ai_analysis_error_code": failure_code,
                "ai_analysis_error": failure_message,
            }
        )

    @classmethod
    def _enrich_sync(
        cls,
        report: ReportDocument,
        config: AIProviderConfig,
        checkpoint: JobCheckpoint | None = None,
    ) -> ReportDocument:
        return asyncio.run(cls._enrich_async(report, config, checkpoint))


class StaticScanJobHandler(JobHandler):
    """Execute validated local scan jobs through the shared application service."""

    def __init__(self, service: StaticScanApplicationService) -> None:
        self.service = service

    def execute(self, job: JobRecord, checkpoint: JobCheckpoint) -> str:
        if job.kind is not JobKind.SCAN:
            raise ValueError("StaticScanJobHandler only accepts scan jobs")
        payload = StaticScanJobPayload.model_validate(job.payload)
        if payload.source_kind == "local" and payload.path is not None:
            history_id, _report = self.service.run_local(
                Path(payload.path),
                config_path=Path(payload.config_path) if payload.config_path else None,
                checkpoint=checkpoint,
                ai_config=payload.ai,
                rag_config=payload.rag,
                source_name=payload.source_name,
            )
        elif (
            payload.source_kind == "openwebui"
            and payload.openwebui_base_url is not None
            and payload.openwebui_knowledge_id is not None
            and payload.credential_ref is not None
        ):
            history_id, _report = self.service.run_openwebui(
                base_url=payload.openwebui_base_url,
                knowledge_id=payload.openwebui_knowledge_id,
                credential_ref=payload.credential_ref,
                content_consent=payload.content_consent,
                checkpoint=checkpoint,
                ai_config=payload.ai,
                rag_config=payload.rag,
                source_name=payload.source_name,
            )
        elif payload.source_kind == "website" and payload.website_url is not None:
            history_id, _report = self.service.run_website(
                url=payload.website_url,
                credential_ref=payload.credential_ref,
                content_consent=payload.content_consent,
                checkpoint=checkpoint,
                ai_config=payload.ai,
                rag_config=payload.rag,
                source_name=payload.source_name,
            )
        else:
            raise ValueError("Scan job source configuration is incomplete")
        return f"history:{history_id}"


def resolve_secret_reference(reference: str) -> str:
    if reference.startswith("file-secret:"):
        return resolve_file_secret_reference(reference)
    if not reference.startswith("env:"):
        raise ValueError("The credential reference type is unsupported")
    name = reference.removeprefix("env:")
    if not name or name not in os.environ or not os.environ[name].strip():
        raise ValueError("The referenced credential environment variable is unavailable")
    return os.environ[name]


def build_pipeline_report(
    result: StaticPipelineResult,
    *,
    show_absolute_paths: bool = False,
    maximum_findings: int = 500,
) -> ReportDocument:
    return ReportBuilder(
        filters=ReportFilter(),
        limits=ReportLimits(maximum_findings=maximum_findings),
        show_absolute_paths=show_absolute_paths,
    ).build(pipeline_report_input(result))


def pipeline_report_input(result: StaticPipelineResult) -> ReportInput:
    parser_messages = [
        warning.message for values in result.parser_warnings.values() for warning in values
    ]
    normalization_messages = [
        warning for values in result.normalization_warnings.values() for warning in values
    ]
    chunking_messages = [
        warning for values in result.chunking_warnings.values() for warning in values
    ]
    skipped_checks = [
        f"{item.stage.value}: {item.relative_path or item.item_id}: {item.reason}"
        for item in result.skipped_items
    ]
    skipped_checks.extend(
        f"{error.stage.value}: {error.code}" for error in result.errors if not error.fatal
    )
    ingestion_issues: list[dict[str, Any]] = []
    matched_items: set[tuple[str, str]] = set()
    for error in result.errors:
        if error.item_id is None and error.relative_path is None:
            continue
        path = error.relative_path or error.item_id or "unknown"
        matched_items.add((error.item_id or "", path))
        remediation = error.metadata.get("remediation")
        ingestion_issues.append(
            {
                "path": path,
                "stage": error.stage.value,
                "code": error.code,
                "message": error.message,
                "remediation": remediation if isinstance(remediation, str) else None,
                "fatal": error.fatal,
            }
        )
    for item in result.skipped_items:
        path = item.relative_path or item.item_id
        if (item.item_id, path) in matched_items:
            continue
        ingestion_issues.append(
            {
                "path": path,
                "stage": item.stage.value,
                "code": "item_skipped",
                "message": item.reason,
                "remediation": "Review the file and scanner limits, then run the scan again.",
                "fatal": False,
            }
        )
    return ReportInput(
        scan=result.scan,
        findings=result.findings,
        scores=result.score_summary,
        score_policy_details=result.score_policy,
        rag_configuration_advice=result.rag_configuration_advice,
        duplicate_groups=result.duplicate_groups,
        chunk_quality_statistics=result.quality_statistics,
        security_statistics=result.security_statistics,
        documents_parsed=len(result.documents),
        rules_evaluated_count=(
            result.security_statistics.rules_evaluated if result.security_statistics else 0
        ),
        rules_skipped_count=(
            result.security_statistics.rules_skipped if result.security_statistics else 0
        ),
        skipped_checks=skipped_checks,
        warnings=parser_messages + normalization_messages + chunking_messages,
        errors=[f"{error.stage.value}: {error.message}" for error in result.errors],
        configuration_summary={
            "offline": bool(result.metadata.get("offline", True)),
            "network_calls": bool(result.metadata.get("network_calls", False)),
            "external_ai": False,
            "rag_profile": result.rag_configuration_advice.profile.value,
            "score_policy_version": result.score_policy.policy_version,
        },
        methodology=[
            "Static security rules, normalized-content duplicate analysis, and chunk-quality heuristics"
        ],
        limitations=[
            "Scores are RAGScanner product-defined and do not prove retrieval or answer quality.",
            "Retrieval quality, answer reliability, freshness, and RAG Rot were not assessed.",
        ],
        generated_at=result.completed_at,
        metadata={"cancelled": result.cancelled},
        knowledge_base_mode=result.knowledge_base_mode,
        source_count=len(result.documents),
        assessment_coverage={
            name: value.model_dump(mode="json")
            for name, value in result.assessment_coverage.items()
        },
        ingestion_issues=ingestion_issues,
    )
