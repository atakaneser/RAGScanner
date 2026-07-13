"""RAGScanner local command-line interface."""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from ragscanner.api import create_app
from ragscanner.application import (
    DurableWorker,
    HistoryApplicationService,
    HistoryNotFoundError,
    JobApplicationService,
    StaticScanApplicationService,
    StaticScanJobHandler,
    pipeline_report_input,
)
from ragscanner.chunking import DocumentChunker
from ragscanner.config import get_settings
from ragscanner.domain import (
    EvaluationClassification,
    ScanStatus,
    Severity,
    SourceContent,
    SourceItem,
)
from ragscanner.jobs import JobKind, JobNotFoundError, JobStateError
from ragscanner.logging import configure_logging
from ragscanner.models import ComponentStatus, DoctorReport
from ragscanner.normalization import DocumentNormalizer
from ragscanner.onboarding import (
    OpenWebUIDiscoveryError,
    discover_local_sources,
    discover_openwebui_files,
    discover_openwebui_knowledge_bases,
    discover_openwebui_services,
)
from ragscanner.parsers import (
    DOCX_MIME,
    DocumentParser,
    DocxParser,
    MarkdownParser,
    PdfParser,
    PlainTextParser,
)
from ragscanner.pipeline import (
    OutputFormat,
    ProgressMode,
    StaticPipelineConfig,
    StaticPipelineResult,
    StaticScanPipeline,
    TerminalStaticScanEventSink,
    load_local_scan_config,
    run_static_pipeline,
)
from ragscanner.quality import (
    ChunkQualityConfig,
    ChunkQualityScanner,
    ExactDuplicateScanner,
    NearDuplicateConfig,
    NearDuplicateScanner,
)
from ragscanner.reporting import (
    HtmlReporter,
    JsonReporter,
    ReportBuilder,
    ReportFilter,
    ReportInput,
    ReportLimits,
    TerminalReporter,
)
from ragscanner.security import (
    StaticRuleLibrary,
    StaticRuleSelection,
    StaticScanConfig,
    StaticSecurityScanner,
)
from ragscanner.storage import SQLiteJobRepository, SQLiteScanHistoryRepository
from ragscanner.storage.database import StorageError
from ragscanner.version import __version__

app = typer.Typer(
    help="Local-first RAG health and security scanner.",
    invoke_without_command=True,
    no_args_is_help=False,
)
security_app = typer.Typer(help="Offline and authorized security scanning commands.")
quality_app = typer.Typer(help="Offline duplicate and chunk-quality analysis commands.")
history_app = typer.Typer(help="Opt-in local SQLite scan history and comparison commands.")
jobs_app = typer.Typer(help="Durable local scan job commands.")
app.add_typer(security_app, name="security")
app.add_typer(quality_app, name="quality")
app.add_typer(history_app, name="history")
app.add_typer(jobs_app, name="jobs")


def _static_rule_directory() -> Path:
    packaged = Path(__file__).resolve().parent / "rules" / "static"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[4] / "rules" / "static"


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"RAGScanner {__version__}")
        raise typer.Exit()


def _run_uv_tool(*arguments: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        typer.echo(
            "uv was not found on PATH. Install uv, restart the terminal, and try again.",
            err=True,
        )
        raise typer.Exit(code=1)
    result = subprocess.run([uv, "tool", *arguments], check=False)  # noqa: S603
    if result.returncode != 0:
        typer.echo(
            f"Maintenance command failed with exit code {result.returncode}.",
            err=True,
        )
        raise typer.Exit(code=result.returncode)


def _run_guided_local_scan(path: Path, *, html_report: bool) -> None:
    output = Path("ragscanner-report.html") if html_report else None
    if output is not None and output.exists():
        suffix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        output = Path(f"ragscanner-report-{suffix}.html")
    unified_scan(
        path=path,
        output_format="html" if html_report else "terminal",
        output=output,
        include=None,
        exclude=None,
        recursive=None,
        max_file_size=None,
        max_files=None,
        category=None,
        exclude_rule=None,
        include_pii=None,
        min_severity=None,
        fail_on=None,
        max_findings=None,
        config_file=None,
        security_only=False,
        quality_only=False,
        quiet=False,
        verbose=False,
        no_color=False,
        save_history=False,
        history_db=None,
    )


def _prompt_choice(prompt: str, choices: set[str], *, default: str) -> str:
    while True:
        value = str(typer.prompt(prompt, default=default)).strip()
        if value in choices:
            return value
        typer.echo(f"Invalid choice. Enter one of: {', '.join(sorted(choices))}")


def _guided_onboarding() -> None:
    typer.echo("Welcome to RAGScanner.")
    typer.echo("What would you like to scan?")
    typer.echo("  1. A local file or folder")
    typer.echo("  2. An OpenWebUI knowledge base")
    typer.echo("  3. Another RAG platform or vector store")
    typer.echo("  4. Exit")
    choice = _prompt_choice("Your choice", {"1", "2", "3", "4"}, default="1")
    if choice == "4":
        typer.echo("No action was taken.")
        return
    if choice == "2":
        typer.echo("RAGScanner requires separate consent before accessing document content.")
        service_candidates = []
        if typer.confirm("Inspect local container runtimes and common loopback addresses?"):
            service_candidates = discover_openwebui_services(include_container_runtimes=True)
            if service_candidates:
                typer.echo("Possible OpenWebUI services:")
                for service_candidate in service_candidates:
                    origin = (
                        f" via {service_candidate.runtime}" if service_candidate.runtime else ""
                    )
                    typer.echo(
                        f"- {service_candidate.base_url} "
                        f"({service_candidate.health_path} responded{origin})"
                    )
            else:
                typer.echo("No responsive OpenWebUI candidate was found on loopback.")
        if service_candidates and typer.confirm(
            "List accessible knowledge bases using an OpenWebUI API key?"
        ):
            selected = service_candidates[0]
            if len(service_candidates) > 1:
                for index, candidate in enumerate(service_candidates, start=1):
                    typer.echo(f"  {index}. {candidate.base_url}")
                selected_index = int(
                    _prompt_choice(
                        "OpenWebUI service",
                        {str(index) for index in range(1, len(service_candidates) + 1)},
                        default="1",
                    )
                )
                selected = service_candidates[selected_index - 1]
            api_key = typer.prompt("OpenWebUI API key", hide_input=True)
            try:
                knowledge_bases = discover_openwebui_knowledge_bases(
                    selected.base_url, str(api_key)
                )
                files = discover_openwebui_files(selected.base_url, str(api_key))
            except OpenWebUIDiscoveryError as error:
                typer.echo(f"Knowledge-base discovery failed: {error}", err=True)
            else:
                if knowledge_bases:
                    typer.echo("Accessible OpenWebUI knowledge bases:")
                    for knowledge_base in knowledge_bases:
                        typer.echo(f"- {knowledge_base.name} ({knowledge_base.id})")
                else:
                    typer.echo("No accessible OpenWebUI knowledge bases were returned.")
                linked_files = sum(bool(item.knowledge_base_ids) for item in files)
                standalone_files = len(files) - linked_files
                typer.echo(
                    "Accessible OpenWebUI file inventory: "
                    f"{linked_files} knowledge-linked, {standalone_files} standalone."
                )
        typer.echo("Metadata inventory does not retrieve document content.")
        typer.echo(
            "To queue a consented content scan, use `ragscanner jobs enqueue-openwebui --help`, "
            "then run `ragscanner worker`."
        )
        return
    if choice == "3":
        typer.echo(
            "Other connectors are not implemented yet. Each source type will use the same safe "
            "SourceConnector contract."
        )
        return

    local_candidates = discover_local_sources(Path.cwd())
    default_path = str(local_candidates[0].path) if local_candidates else "."
    if local_candidates:
        typer.echo("Nearby source candidates:")
        for local_candidate in local_candidates[:5]:
            typer.echo(
                f"- {local_candidate.path} ({local_candidate.supported_file_count} supported files)"
            )
    value = typer.prompt("File or folder to scan", default=default_path)
    path = Path(value).expanduser()
    if not path.exists():
        raise typer.BadParameter(f"path not found: {path}")
    html_report = typer.confirm("Create a standalone HTML report?", default=True)
    _run_guided_local_scan(path, html_report=html_report)


@app.callback()
def main(
    context: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """RAGScanner command group."""
    if context.invoked_subcommand is None and not version:
        _guided_onboarding()


@app.command()
def doctor() -> None:
    """Validate the local scaffold configuration without network access."""
    settings = get_settings()
    configure_logging(settings.log_level)
    report = DoctorReport(
        version=__version__,
        configuration=ComponentStatus(ok=True, detail="environment configuration valid"),
        network=ComponentStatus(ok=True, detail="no network request performed"),
    )
    typer.echo(f"OK version: {report.version}")
    typer.echo(f"OK configuration: {report.configuration.detail}")
    typer.echo(f"OK network: {report.network.detail}")


@app.command()
def update() -> None:
    """Upgrade the installed RAGScanner tool through uv."""
    typer.echo("Updating RAGScanner through uv...")
    _run_uv_tool("upgrade", "ragscanner")
    typer.echo("RAGScanner update completed.")


@app.command()
def repair() -> None:
    """Reinstall the current RAGScanner tool environment through uv."""
    typer.echo("Repairing the RAGScanner installation through uv...")
    _run_uv_tool("upgrade", "ragscanner", "--reinstall")
    typer.echo("RAGScanner repair completed.")


@app.command()
def uninstall(
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the uninstall confirmation."),
    ] = False,
) -> None:
    """Remove the installed RAGScanner tool through uv."""
    if not yes and not typer.confirm("Uninstall RAGScanner from this user account?"):
        typer.echo("Uninstall cancelled. No changes were made.")
        return
    typer.echo("Uninstalling RAGScanner through uv...")
    _run_uv_tool("uninstall", "ragscanner")
    typer.echo("RAGScanner uninstall completed.")


def _pipeline_report_input(result: StaticPipelineResult) -> ReportInput:
    return pipeline_report_input(result)


def _atomic_write(path: Path, value: str, config: StaticPipelineConfig) -> None:
    parent = path.parent
    if not parent.exists():
        if not config.create_output_parents:
            raise ValueError("output parent does not exist")
        parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not config.allow_output_overwrite:
        raise ValueError("output already exists; overwrite is disabled")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@app.command("scan")
def unified_scan(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_format: Annotated[str | None, typer.Option("--format")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    include: Annotated[str | None, typer.Option("--include")] = None,
    exclude: Annotated[str | None, typer.Option("--exclude")] = None,
    recursive: Annotated[bool | None, typer.Option("--recursive/--no-recursive")] = None,
    max_file_size: Annotated[int | None, typer.Option("--max-file-size", min=1)] = None,
    max_files: Annotated[int | None, typer.Option("--max-files", min=1)] = None,
    category: Annotated[str | None, typer.Option("--category")] = None,
    exclude_rule: Annotated[str | None, typer.Option("--exclude-rule")] = None,
    include_pii: Annotated[bool | None, typer.Option("--include-pii/--no-include-pii")] = None,
    min_severity: Annotated[str | None, typer.Option("--min-severity")] = None,
    fail_on: Annotated[str | None, typer.Option("--fail-on")] = None,
    max_findings: Annotated[int | None, typer.Option("--max-findings", min=1)] = None,
    config_file: Annotated[
        Path | None, typer.Option("--config", exists=True, dir_okay=False)
    ] = None,
    security_only: Annotated[bool, typer.Option("--security-only")] = False,
    quality_only: Annotated[bool, typer.Option("--quality-only")] = False,
    quiet: Annotated[bool, typer.Option("--quiet")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
    save_history: Annotated[bool, typer.Option("--save-history")] = False,
    history_db: Annotated[Path | None, typer.Option("--history-db", dir_okay=False)] = None,
) -> None:
    """Run the complete local static scan pipeline and render a report."""
    del no_color  # Output is deliberately ANSI-free in the first implementation.
    if security_only and quality_only:
        raise typer.BadParameter("security-only and quality-only are mutually exclusive")
    if quiet and verbose:
        raise typer.BadParameter("quiet and verbose are mutually exclusive")
    try:
        file_config = load_local_scan_config(config_file)
        config = file_config.pipeline_config(path.resolve())
        if path.is_file() and path.suffix.casefold() not in config.allowed_extensions:
            raise ValueError("single-file scan supports only TXT, Markdown, PDF, or DOCX")
        updates: dict[str, object] = {}
        if output_format is not None:
            updates["output_format"] = OutputFormat(output_format)
        if output is not None:
            updates["output_path"] = output
        if include is not None:
            updates["include_patterns"] = sorted(_csv(include))
        if exclude is not None:
            updates["exclude_patterns"] = sorted(_csv(exclude))
        if recursive is not None:
            updates["recursive"] = recursive
        if max_file_size is not None:
            updates["maximum_file_size"] = max_file_size
        if max_files is not None:
            updates["maximum_discovered_files"] = max_files
        if max_findings is not None:
            updates["maximum_findings"] = max_findings
        if min_severity is not None:
            updates["minimum_severity"] = Severity(min_severity)
        if fail_on is not None:
            updates["fail_on_severity"] = Severity(fail_on)
        if quiet:
            updates["progress_mode"] = ProgressMode.QUIET
        elif verbose:
            updates["progress_mode"] = ProgressMode.VERBOSE
        if security_only:
            updates.update(
                exact_duplicates_enabled=False,
                near_duplicates_enabled=False,
                chunk_quality_enabled=False,
            )
        if quality_only:
            updates["security_enabled"] = False
        config = config.model_copy(update=updates)
        selection_updates: dict[str, object] = {}
        if category is not None:
            selection_updates["categories"] = _csv(category)
        if exclude_rule is not None:
            selection_updates["excluded_rule_ids"] = _csv(exclude_rule)
        if include_pii is not None:
            selection_updates["include_pii"] = include_pii
        if selection_updates:
            selection = config.security.selection.model_copy(update=selection_updates)
            config = config.model_copy(
                update={"security": config.security.model_copy(update={"selection": selection})}
            )
        config = StaticPipelineConfig.model_validate(config.model_dump())
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    sink = None
    if config.progress_mode is not ProgressMode.QUIET:
        sink = TerminalStaticScanEventSink(
            lambda message: typer.echo(message, err=True),
            verbose=config.progress_mode is ProgressMode.VERBOSE,
        )
    pipeline = StaticScanPipeline(config, event_sink=sink)
    try:
        result = run_static_pipeline(pipeline)
    except KeyboardInterrupt:
        pipeline.cancel()
        raise typer.Exit(code=130) from None
    report_filter = ReportFilter(
        minimum_severity=config.minimum_severity,
        include_informational=True,
    )
    limits = ReportLimits(maximum_findings=config.maximum_findings)
    pipeline.report_started(result.scan.id)
    report = ReportBuilder(
        filters=report_filter,
        limits=limits,
        show_absolute_paths=not config.show_relative_paths,
    ).build(_pipeline_report_input(result))
    if save_history or history_db is not None:
        database_path = history_db or (get_settings().data_dir / "history.sqlite3")
        repository: SQLiteScanHistoryRepository | None = None
        try:
            repository = SQLiteScanHistoryRepository(database_path)
            history_id = repository.save(report)
        except (OSError, StorageError, ValueError) as error:
            typer.echo(f"local history save failed: {error}", err=True)
            raise typer.Exit(code=1) from error
        finally:
            if repository is not None:
                repository.close()
        if not quiet:
            typer.echo(f"Scan saved to local history: {history_id}", err=True)
    if config.output_format is OutputFormat.JSON:
        rendered = JsonReporter().render(report, limits=limits)
    elif config.output_format is OutputFormat.HTML:
        rendered = HtmlReporter().render(report, limits=limits)
    else:
        rendered = TerminalReporter().render(report, verbose=verbose)
    if config.output_path is not None:
        try:
            _atomic_write(config.output_path, rendered, config)
        except (OSError, ValueError) as error:
            typer.echo(f"report write failed: {error}", err=True)
            raise typer.Exit(code=1) from error
        if not quiet:
            typer.echo(f"Report written: {config.output_path}")
    else:
        typer.echo(rendered, nl=False)
    pipeline.report_completed(result.scan.id)
    if result.cancelled:
        raise typer.Exit(code=130)
    if result.scan.status is ScanStatus.FAILED:
        raise typer.Exit(code=1)
    if config.fail_on_severity is not None:
        rank = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        if any(rank[item.severity] >= rank[config.fail_on_severity] for item in result.findings):
            raise typer.Exit(code=3)


def _history_database(database: Path | None) -> Path:
    return database or (get_settings().data_dir / "history.sqlite3")


def _job_service(database: Path | None) -> tuple[SQLiteJobRepository, JobApplicationService]:
    repository = SQLiteJobRepository(_history_database(database))
    return repository, JobApplicationService(repository)


@jobs_app.command("enqueue-scan")
def jobs_enqueue_scan(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    config_file: Annotated[
        Path | None, typer.Option("--config", exists=True, dir_okay=False)
    ] = None,
    idempotency_key: Annotated[str | None, typer.Option("--idempotency-key")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", min=1, max=10)] = 3,
) -> None:
    """Queue a local static scan without starting an in-process task."""
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        job = service.enqueue_local_scan(
            path,
            config_path=config_file,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
        )
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot enqueue scan job: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(f"Queued scan job: {job.id}")


@jobs_app.command("list")
def jobs_list(
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 50,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
) -> None:
    """List durable jobs without exposing source content."""
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        page = service.list(limit=limit, offset=offset)
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot read jobs: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    if output_format == "json":
        typer.echo(page.model_dump_json())
        return
    typer.echo(f"Durable jobs: {page.total} record(s)")
    for job in page.items:
        typer.echo(
            f"- {job.id} | {job.kind.value} | {job.status.value} | "
            f"attempts={job.attempt_count}/{job.max_attempts} | progress={job.progress:.0%}"
        )


@jobs_app.command("enqueue-openwebui")
def jobs_enqueue_openwebui(
    base_url: Annotated[str, typer.Option("--base-url")],
    knowledge_id: Annotated[str, typer.Option("--knowledge-id")],
    credential_ref: Annotated[str, typer.Option("--credential-ref")],
    consent_content: Annotated[bool, typer.Option("--consent-content")] = False,
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    idempotency_key: Annotated[str | None, typer.Option("--idempotency-key")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", min=1, max=10)] = 3,
) -> None:
    """Queue a consented OpenWebUI knowledge-base content scan."""
    if not consent_content:
        raise typer.BadParameter("OpenWebUI scans require --consent-content")
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        job = service.enqueue_openwebui_scan(
            base_url=base_url,
            knowledge_id=knowledge_id,
            credential_ref=credential_ref,
            content_consent=True,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
        )
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot enqueue OpenWebUI scan job: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(f"Queued OpenWebUI scan job: {job.id}")


@jobs_app.command("show")
def jobs_show(
    job_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
) -> None:
    """Show one durable job as stable JSON."""
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        job = service.get(job_id)
    except JobNotFoundError:
        typer.echo(f"Job was not found: {job_id}", err=True)
        raise typer.Exit(code=1) from None
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot read job: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(job.model_dump_json())


@jobs_app.command("cancel")
def jobs_cancel(
    job_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
) -> None:
    """Request immediate or cooperative cancellation for one job."""
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        job = service.cancel(job_id)
    except JobNotFoundError:
        typer.echo(f"Job was not found: {job_id}", err=True)
        raise typer.Exit(code=1) from None
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot cancel job: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(f"Job status: {job.status.value}")


@jobs_app.command("retry")
def jobs_retry(
    job_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
) -> None:
    """Requeue one failed or cancelled job with a fresh attempt budget."""
    repository: SQLiteJobRepository | None = None
    try:
        repository, service = _job_service(database)
        job = service.retry(job_id)
    except JobNotFoundError:
        typer.echo(f"Job was not found: {job_id}", err=True)
        raise typer.Exit(code=1) from None
    except JobStateError as error:
        raise typer.BadParameter(str(error)) from error
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot retry job: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(f"Job requeued: {job.id}")


@app.command("worker")
def worker_command(
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    once: Annotated[bool, typer.Option("--once")] = False,
    poll_interval: Annotated[float, typer.Option("--poll-interval", min=0.1, max=60)] = 1,
    lease_seconds: Annotated[int, typer.Option("--lease-seconds", min=5, max=3600)] = 30,
    worker_id: Annotated[str | None, typer.Option("--worker-id")] = None,
) -> None:
    """Run the durable local scan worker."""
    from datetime import timedelta

    selected_database = _history_database(database)
    job_repository: SQLiteJobRepository | None = None
    history_repository: SQLiteScanHistoryRepository | None = None
    try:
        job_repository = SQLiteJobRepository(selected_database)
        history_repository = SQLiteScanHistoryRepository(selected_database)
        handler = StaticScanJobHandler(StaticScanApplicationService(history_repository))
        worker = DurableWorker(
            job_repository,
            {JobKind.SCAN: handler},
            worker_id=worker_id or f"{socket.gethostname()}:{os.getpid()}",
            lease_duration=timedelta(seconds=lease_seconds),
        )
        typer.echo(f"Worker started with database {selected_database}.", err=True)
        while True:
            job = worker.run_once()
            if job is not None:
                typer.echo(f"Job {job.id}: {job.status.value}", err=True)
            if once:
                break
            if job is None:
                time.sleep(poll_interval)
    except KeyboardInterrupt:
        typer.echo("Worker stopped.", err=True)
    except (OSError, StorageError, ValueError) as error:
        typer.echo(f"Worker failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if history_repository is not None:
            history_repository.close()
        if job_repository is not None:
            job_repository.close()


@app.command("serve")
def serve_api(
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    history_db: Annotated[Path | None, typer.Option("--history-db", dir_okay=False)] = None,
) -> None:
    """Serve the local dashboard and authenticated job API on loopback only."""
    database = _history_database(history_db)
    typer.echo(
        f"Starting the local dashboard and API at http://127.0.0.1:{port} "
        f"with history/job database {database}.",
        err=True,
    )
    uvicorn.run(
        create_app(database),
        host="127.0.0.1",
        port=port,
        access_log=False,
        server_header=False,
    )


@history_app.command("list")
def history_list(
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 50,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
) -> None:
    """List paginated local scan history without reading report evidence."""
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    repository: SQLiteScanHistoryRepository | None = None
    try:
        repository = SQLiteScanHistoryRepository(_history_database(database))
        page = HistoryApplicationService(repository).list(limit=limit, offset=offset)
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot read local history: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    if output_format == "json":
        typer.echo(page.model_dump_json())
        return
    typer.echo(f"Local scan history: {page.total} record(s)")
    for item in page.items:
        score = f"{item.overall_score:.2f}" if item.overall_score is not None else "not assessed"
        typer.echo(
            f"- {item.history_id} | scan={item.scan_id} | {item.status} | "
            f"{item.source_name or 'unknown source'} | "
            f"findings={item.finding_count} | overall={score}"
        )


@history_app.command("show")
def history_show(
    scan_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Render one persisted report snapshot."""
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    repository: SQLiteScanHistoryRepository | None = None
    try:
        repository = SQLiteScanHistoryRepository(_history_database(database))
        report = HistoryApplicationService(repository).get(scan_id)
    except HistoryNotFoundError:
        typer.echo(f"Scan was not found in local history: {scan_id}", err=True)
        raise typer.Exit(code=1) from None
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot read local history: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    if output_format == "json":
        typer.echo(report.model_dump_json())
    else:
        typer.echo(TerminalReporter().render(report, verbose=verbose), nl=False)


@history_app.command("compare")
def history_compare(
    baseline_scan_id: Annotated[str, typer.Argument()],
    candidate_scan_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
) -> None:
    """Compare two persisted scans with coverage-aware finding semantics."""
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    repository: SQLiteScanHistoryRepository | None = None
    try:
        repository = SQLiteScanHistoryRepository(_history_database(database))
        comparison = HistoryApplicationService(repository).compare(
            baseline_scan_id, candidate_scan_id
        )
    except HistoryNotFoundError as error:
        typer.echo(f"Scan was not found in local history: {', '.join(error.history_ids)}", err=True)
        raise typer.Exit(code=1) from None
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot read local history: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    if output_format == "json":
        typer.echo(comparison.model_dump_json())
        return
    typer.echo(
        f"Scan comparison: {baseline_scan_id} -> {candidate_scan_id}\n"
        f"Compatible: {'yes' if comparison.compatible else 'no'}\n"
        f"New: {len(comparison.new_findings)} | "
        f"Resolved: {len(comparison.resolved_findings)} | "
        f"Not observed: {len(comparison.not_observed_findings)} | "
        f"Recurring: {len(comparison.recurring_findings)} | "
        f"Severity changes: {len(comparison.severity_changes)}"
    )
    for warning in comparison.warnings:
        typer.echo(f"WARNING: {warning}")


@history_app.command("delete")
def history_delete(
    scan_id: Annotated[str, typer.Argument()],
    database: Annotated[Path | None, typer.Option("--database", dir_okay=False)] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
) -> None:
    """Delete one local history record after confirmation."""
    if not yes and not typer.confirm(f"Delete local scan history record {scan_id}?"):
        typer.echo("History deletion cancelled.")
        return
    repository: SQLiteScanHistoryRepository | None = None
    try:
        repository = SQLiteScanHistoryRepository(_history_database(database))
        HistoryApplicationService(repository).delete(scan_id)
    except HistoryNotFoundError:
        typer.echo(f"Scan was not found in local history: {scan_id}", err=True)
        raise typer.Exit(code=1) from None
    except (OSError, StorageError, ValueError) as error:
        raise typer.BadParameter(f"cannot update local history: {error}") from error
    finally:
        if repository is not None:
            repository.close()
    typer.echo(f"Deleted local scan history record: {scan_id}")


@app.command("report")
def report_command(
    scan_result: Annotated[Path, typer.Argument(exists=True, readable=True, dir_okay=False)],
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
    output: Annotated[Path | None, typer.Option("--output")] = None,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    severity: Annotated[str | None, typer.Option("--severity")] = None,
    category: Annotated[str | None, typer.Option("--category")] = None,
    classification: Annotated[str | None, typer.Option("--classification")] = None,
    rule_id: Annotated[str | None, typer.Option("--rule-id")] = None,
    document: Annotated[str | None, typer.Option("--document")] = None,
    target: Annotated[str | None, typer.Option("--target")] = None,
    max_findings: Annotated[int, typer.Option("--max-findings", min=1)] = 500,
    include_info: Annotated[bool, typer.Option("--include-info/--exclude-info")] = True,
    show_absolute_paths: Annotated[bool, typer.Option("--show-absolute-paths")] = False,
) -> None:
    """Render a validated report aggregate without a database or network access."""
    if output_format not in {"terminal", "json", "html"}:
        raise typer.BadParameter("format must be terminal, json, or html")
    if output_format == "html" and output is None:
        raise typer.BadParameter("HTML reports require --output")
    try:
        minimum_severity = Severity(severity) if severity else None
        classifications = {EvaluationClassification(item) for item in _csv(classification)}
        report_input = ReportInput.model_validate_json(scan_result.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(f"invalid report input: {error}") from error
    filters = ReportFilter(
        minimum_severity=minimum_severity,
        categories=_csv(category),
        classifications=classifications,
        document_id=document,
        target_id=target,
        rule_ids=_csv(rule_id),
        include_informational=include_info,
    )
    limits = ReportLimits(maximum_findings=max_findings)
    report = ReportBuilder(
        filters=filters,
        limits=limits,
        show_absolute_paths=show_absolute_paths,
    ).build(report_input)
    if output_format == "json":
        rendered = JsonReporter().render(report, limits=limits)
    elif output_format == "html":
        rendered = HtmlReporter().render(report, limits=limits)
    else:
        rendered = TerminalReporter().render(report, verbose=verbose)
    if output is None:
        typer.echo(rendered, nl=False)
        return
    try:
        output.write_text(rendered, encoding="utf-8")
    except OSError as error:
        raise typer.BadParameter(f"cannot write report: {error}") from error
    typer.echo(f"Report written: {output}")


def _parse_local_file(path: Path):  # type: ignore[no-untyped-def]
    data = path.read_bytes()
    if len(data) > 25 * 1024 * 1024:
        raise ValueError("input file exceeds the CLI safety limit")
    suffix = path.suffix.casefold()
    mime = {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".pdf": "application/pdf",
        ".docx": DOCX_MIME,
    }.get(suffix)
    if mime is None:
        raise ValueError(f"unsupported file type: {suffix or '<none>'}")
    now = datetime.now(UTC)
    source = SourceContent(
        item=SourceItem(
            id=f"cli:{path.resolve()}",
            source_id="cli-filesystem",
            external_id=str(path.resolve()),
            name=path.name,
            path=str(path.resolve()),
            mime_type=mime,
            size_bytes=len(data),
            modified_at=datetime.fromtimestamp(path.stat().st_mtime, UTC),
        ),
        content_bytes=data,
        content_type=mime,
        retrieved_at=now,
        limit_bytes=max(1, len(data)),
    )
    parsers: dict[str, DocumentParser] = {
        "text/plain": PlainTextParser(),
        "text/markdown": MarkdownParser(),
        "application/pdf": PdfParser(),
        DOCX_MIME: DocxParser(),
    }
    parser = parsers[mime]
    return parser.parse(source)


def _csv(value: str | None) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


@security_app.command("scan")
def security_scan(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    rules: Annotated[str | None, typer.Option("--rules")] = None,
    exclude_rule: Annotated[str | None, typer.Option("--exclude-rule")] = None,
    category: Annotated[str | None, typer.Option("--category")] = None,
    severity: Annotated[str | None, typer.Option("--severity")] = None,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
    fail_on: Annotated[str | None, typer.Option("--fail-on")] = None,
    max_findings: Annotated[int, typer.Option("--max-findings", min=1)] = 500,
    include_pii: Annotated[bool, typer.Option("--include-pii")] = False,
    offline: Annotated[bool, typer.Option("--offline/--no-offline")] = True,
) -> None:
    """Scan local supported documents with deterministic static rules."""
    if not offline:
        raise typer.BadParameter("static security scanning is offline-only")
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    try:
        selected_severities = {Severity(item) for item in _csv(severity)}
        fail_severity = Severity(fail_on) if fail_on else None
    except ValueError as error:
        raise typer.BadParameter("invalid severity value") from error
    library = StaticRuleLibrary.from_directory(_static_rule_directory())
    selection = StaticRuleSelection(
        rule_ids=_csv(rules),
        excluded_rule_ids=_csv(exclude_rule),
        categories=_csv(category),
        severities=selected_severities,
        include_pii=include_pii,
    )
    scanner = StaticSecurityScanner(
        library,
        StaticScanConfig(selection=selection, maximum_findings_per_document=max_findings),
    )
    supported = {".txt", ".md", ".markdown", ".pdf", ".docx"}
    files = (
        [path]
        if path.is_file()
        else sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.casefold() in supported
        )
    )
    results = []
    for file_path in files:
        try:
            parsed = _parse_local_file(file_path)
            normalized = DocumentNormalizer().normalize(parsed.document)
            chunks = DocumentChunker().chunk(parsed.document, normalized).chunks
            results.append(
                scanner.scan(
                    parsed.document,
                    normalized=normalized,
                    chunks=chunks,
                    parser_warnings=parsed.warnings,
                )
            )
        except (OSError, ValueError) as error:
            raise typer.BadParameter(f"cannot scan {file_path.name}: {error}") from error
    if output_format == "json":
        typer.echo(
            json.dumps(
                [result.model_dump(mode="json") for result in results],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        finding_count = sum(len(result.findings) for result in results)
        typer.echo(f"Scanned {len(results)} document(s); findings: {finding_count}")
        for result in results:
            for finding in result.findings:
                typer.echo(
                    f"{finding.severity.value.upper():8} {finding.rule_id} "
                    f"{finding.source.source_path if finding.source else '-'}: {finding.title}"
                )
    if fail_severity is not None:
        rank = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        if any(
            rank[finding.severity] >= rank[fail_severity]
            for result in results
            for finding in result.findings
        ):
            raise typer.Exit(code=2)


@quality_app.command("scan")
def quality_scan(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    exact_duplicates: Annotated[
        bool, typer.Option("--exact-duplicates/--no-exact-duplicates")
    ] = True,
    near_duplicates: Annotated[bool, typer.Option("--near-duplicates/--no-near-duplicates")] = True,
    chunk_quality: Annotated[bool, typer.Option("--chunk-quality/--no-chunk-quality")] = True,
    similarity_threshold: Annotated[
        float, typer.Option("--similarity-threshold", min=0.5, max=1.0)
    ] = 0.82,
    min_chunk_tokens: Annotated[int, typer.Option("--min-chunk-tokens", min=0)] = 50,
    max_chunk_tokens: Annotated[int, typer.Option("--max-chunk-tokens", min=1)] = 500,
    fail_on: Annotated[str | None, typer.Option("--fail-on")] = None,
    output_format: Annotated[str, typer.Option("--format")] = "terminal",
) -> None:
    """Analyze local documents for duplicates and chunk-quality problems."""
    if not any((exact_duplicates, near_duplicates, chunk_quality)):
        raise typer.BadParameter("at least one quality scanner must be enabled")
    if output_format not in {"terminal", "json"}:
        raise typer.BadParameter("format must be terminal or json")
    if min_chunk_tokens > max_chunk_tokens:
        raise typer.BadParameter("min chunk tokens cannot exceed max chunk tokens")
    try:
        fail_severity = Severity(fail_on) if fail_on else None
    except ValueError as error:
        raise typer.BadParameter("invalid severity value") from error
    supported = {".txt", ".md", ".markdown", ".pdf", ".docx"}
    files = (
        [path]
        if path.is_file()
        else sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.casefold() in supported
        )
    )
    documents = []
    normalized_results = {}
    chunks = []
    for file_path in files:
        try:
            parsed = _parse_local_file(file_path)
            normalized = DocumentNormalizer().normalize(parsed.document)
            document_chunks = DocumentChunker().chunk(parsed.document, normalized).chunks
        except (OSError, ValueError) as error:
            raise typer.BadParameter(f"cannot analyze {file_path.name}: {error}") from error
        documents.append(parsed.document)
        normalized_results[parsed.document.id] = normalized
        chunks.extend(document_chunks)
    payload: dict[str, object] = {}
    all_findings = []
    if exact_duplicates:
        exact = ExactDuplicateScanner().scan(documents, normalized_results, chunks)
        payload["exact_duplicates"] = exact.model_dump(mode="json")
        all_findings.extend(exact.findings)
    if near_duplicates:
        near = NearDuplicateScanner(
            NearDuplicateConfig(similarity_threshold=similarity_threshold)
        ).scan(documents, normalized_results, chunks)
        payload["near_duplicates"] = near.model_dump(mode="json")
        all_findings.extend(near.findings)
    if chunk_quality:
        target = max(min_chunk_tokens, min(300, max_chunk_tokens))
        quality = ChunkQualityScanner(
            ChunkQualityConfig(
                minimum_chunk_tokens=min_chunk_tokens,
                target_chunk_tokens=target,
                maximum_chunk_tokens=max_chunk_tokens,
            )
        ).scan(documents, chunks, normalized_results)
        payload["chunk_quality"] = quality.model_dump(mode="json")
        all_findings.extend(quality.findings)
    if output_format == "json":
        typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        typer.echo(
            f"Analyzed {len(documents)} document(s), {len(chunks)} chunk(s); "
            f"findings: {len(all_findings)}"
        )
        for finding in sorted(all_findings, key=lambda value: value.fingerprint):
            typer.echo(
                f"{finding.severity.value.upper():8} {finding.rule_id} "
                f"{finding.source.source_path if finding.source else '-'}: {finding.title}"
            )
    if fail_severity is not None:
        rank = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        if any(rank[finding.severity] >= rank[fail_severity] for finding in all_findings):
            raise typer.Exit(code=2)
