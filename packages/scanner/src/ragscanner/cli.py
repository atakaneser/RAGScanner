"""RAGScanner local command-line interface."""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ragscanner.chunking import DocumentChunker
from ragscanner.config import get_settings
from ragscanner.domain import (
    EvaluationClassification,
    ScanStatus,
    Severity,
    SourceContent,
    SourceItem,
)
from ragscanner.logging import configure_logging
from ragscanner.models import ComponentStatus, DoctorReport
from ragscanner.normalization import DocumentNormalizer
from ragscanner.onboarding import discover_local_sources, discover_openwebui_services
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
from ragscanner.version import __version__

app = typer.Typer(
    help="Local-first RAG health and security scanner.",
    invoke_without_command=True,
    no_args_is_help=False,
)
security_app = typer.Typer(help="Offline and authorized security scanning commands.")
quality_app = typer.Typer(help="Offline duplicate and chunk-quality analysis commands.")
app.add_typer(security_app, name="security")
app.add_typer(quality_app, name="quality")


def _static_rule_directory() -> Path:
    packaged = Path(__file__).resolve().parent / "rules" / "static"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[4] / "rules" / "static"


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"RAGScanner {__version__}")
        raise typer.Exit()


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
        if typer.confirm("Check common local OpenWebUI addresses?"):
            service_candidates = discover_openwebui_services()
            if service_candidates:
                typer.echo("Possible OpenWebUI services:")
                for service_candidate in service_candidates:
                    typer.echo(
                        f"- {service_candidate.base_url} "
                        f"({service_candidate.health_path} responded)"
                    )
            else:
                typer.echo("No responsive OpenWebUI candidate was found on loopback.")
        typer.echo(
            "The OpenWebUI source connector is not implemented yet; no content was retrieved."
        )
        typer.echo("For now, scan a local export with `ragscanner scan <path>`. ")
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


def _pipeline_report_input(result: StaticPipelineResult) -> ReportInput:
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
    return ReportInput(
        scan=result.scan,
        findings=result.findings,
        scores=result.score_summary,
        duplicate_groups=result.duplicate_groups,
        chunk_quality_statistics=result.quality_statistics,
        security_statistics=result.security_statistics,
        documents_parsed=len(result.documents),
        rules_evaluated_count=result.security_statistics.rules_evaluated
        if result.security_statistics
        else 0,
        rules_skipped_count=result.security_statistics.rules_skipped
        if result.security_statistics
        else 0,
        skipped_checks=skipped_checks,
        warnings=parser_messages + normalization_messages + chunking_messages,
        errors=[f"{error.stage.value}: {error.message}" for error in result.errors],
        configuration_summary={
            "offline": True,
            "network_calls": False,
            "external_ai": False,
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
    )


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
