"""RAGScanner local command-line interface."""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
import uvicorn

from ragscanner.agent import install_autostart, platform_autostart_path, remove_autostart, run_agent
from ragscanner.ai_analysis.service import build_analysis_request
from ragscanner.api import create_app
from ragscanner.application import (
    DurableWorker,
    HistoryApplicationService,
    HistoryNotFoundError,
    JobApplicationService,
    StaticScanApplicationService,
    StaticScanJobHandler,
    pipeline_report_input,
    resolve_secret_reference,
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
from ragscanner.host_service import (
    install_host_service,
    is_elevated,
    remove_host_service,
    service_definition_path,
    system_data_dir,
)
from ragscanner.jobs import JobKind, JobNotFoundError, JobStateError
from ragscanner.local_site import (
    dashboard_url,
    hosts_file_path,
    local_hostname_is_registered,
    register_local_hostname,
    unregister_local_hostname,
)
from ragscanner.logging import configure_logging
from ragscanner.models import ComponentStatus, DoctorReport
from ragscanner.normalization import DocumentNormalizer
from ragscanner.onboarding import (
    OpenWebUIDiscoveryError,
    ServiceCandidate,
    discover_local_rag_environments,
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
from ragscanner.paths import new_report_path, reports_directory
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
from ragscanner.providers import (
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
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
from ragscanner.reporting.models import ReportDocument
from ragscanner.security import (
    StaticRuleLibrary,
    StaticRuleSelection,
    StaticScanConfig,
    StaticSecurityScanner,
)
from ragscanner.storage import (
    SourceProfile,
    SQLiteJobRepository,
    SQLiteScanHistoryRepository,
    SQLiteSourceProfileRepository,
)
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
agent_app = typer.Typer(help="Run and manage the per-user local dashboard Agent.")
site_app = typer.Typer(help="Configure the machine-local dashboard address.")
host_app = typer.Typer(help="Run and manage the machine-wide local Host Service.")
app.add_typer(security_app, name="security")
app.add_typer(quality_app, name="quality")
app.add_typer(history_app, name="history")
app.add_typer(jobs_app, name="jobs")
app.add_typer(agent_app, name="agent")
app.add_typer(site_app, name="site")
app.add_typer(host_app, name="host")


def _static_rule_directory() -> Path:
    packaged = Path(__file__).resolve().parent / "rules" / "static"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[4] / "rules" / "static"


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"RAGScanner {__version__}")
        raise typer.Exit()


def _uv_executable() -> str:
    uv = shutil.which("uv")
    if uv is None:
        typer.echo(
            "uv was not found on PATH. Install uv, restart the terminal, and try again.",
            err=True,
        )
        raise typer.Exit(code=1)
    return uv


def _run_uv_tool(*arguments: str) -> None:
    uv = _uv_executable()
    result = subprocess.run([uv, "tool", *arguments], check=False)  # noqa: S603
    if result.returncode != 0:
        typer.echo(
            f"Maintenance command failed with exit code {result.returncode}.",
            err=True,
        )
        raise typer.Exit(code=result.returncode)


def _schedule_windows_uninstall(uv: str) -> None:
    """Run uv after this Windows launcher has released its executable files."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".cmd", prefix="ragscanner-uninstall-", delete=False
    ) as script:
        script.write(
            "@echo off\r\n"
            "ping 127.0.0.1 -n 3 > nul\r\n"
            f'"{uv}" tool uninstall ragscanner\r\n'
            'del "%~f0"\r\n'
        )
        script_path = script.name
    try:
        subprocess.Popen(  # noqa: S603
            [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", script_path],
            close_fds=True,
            creationflags=(
                getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            ),
        )
    except OSError:
        Path(script_path).unlink(missing_ok=True)
        raise


def _run_guided_local_scan(path: Path, *, html_report: bool = False) -> None:
    """Run a guided scan into local history; HTML is retained only for compatibility."""
    output = new_report_path(get_settings().data_dir) if html_report else None
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
        save_history=not html_report,
        history_db=None,
    )


def _prompt_choice(prompt: str, choices: set[str], *, default: str) -> str:
    while True:
        value = str(typer.prompt(prompt, default=default)).strip()
        if value in choices:
            return value
        typer.echo(f"Invalid choice. Enter one of: {', '.join(sorted(choices))}")


def _guided_openwebui_content_scan(
    service: ServiceCandidate,
    knowledge_base_id: str,
    api_key: str,
) -> None:
    """Run one consented OpenWebUI scan without persisting the supplied API key."""
    secret_name = f"RAGSCANNER_GUIDED_OPENWEBUI_KEY_{uuid4().hex}"
    history_repository: SQLiteScanHistoryRepository | None = None
    os.environ[secret_name] = api_key
    try:
        history_repository = SQLiteScanHistoryRepository(_history_database(None))
        history_id, _report = StaticScanApplicationService(history_repository).run_openwebui(
            base_url=service.base_url,
            knowledge_id=knowledge_base_id,
            credential_ref=f"env:{secret_name}",
            content_consent=True,
        )
    except (OSError, StorageError, ValueError) as error:
        typer.echo(f"OpenWebUI content scan failed: {error}", err=True)
        return
    finally:
        os.environ.pop(secret_name, None)
        if history_repository is not None:
            history_repository.close()
    typer.echo(
        f"OpenWebUI content scan completed. View report {history_id} at "
        f"{dashboard_url()}/reports/{history_id}"
    )


def _guided_openwebui_metadata(
    service_candidates: Sequence[ServiceCandidate], *, offer_content_scan: bool = False
) -> None:
    """List consented OpenWebUI metadata and optionally start one selected content scan."""
    if not service_candidates or not typer.confirm(
        "List accessible knowledge bases using an OpenWebUI API key?"
    ):
        return
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
        knowledge_bases = discover_openwebui_knowledge_bases(selected.base_url, str(api_key))
    except OpenWebUIDiscoveryError as error:
        typer.echo(f"Knowledge-base discovery failed: {error}", err=True)
        return
    if knowledge_bases:
        typer.echo("Accessible OpenWebUI knowledge bases:")
        for knowledge_base in knowledge_bases:
            typer.echo(f"- {knowledge_base.name} ({knowledge_base.id})")
    else:
        typer.echo("No accessible OpenWebUI knowledge bases were returned.")
    try:
        files = discover_openwebui_files(
            selected.base_url,
            str(api_key),
            knowledge_base_ids=(item.id for item in knowledge_bases),
        )
    except OpenWebUIDiscoveryError as error:
        typer.echo(f"File metadata inventory failed: {error}", err=True)
        return
    linked_files = sum(bool(item.knowledge_base_ids) for item in files)
    standalone_files = len(files) - linked_files
    typer.echo(
        "Accessible OpenWebUI file inventory: "
        f"{linked_files} knowledge-linked, {standalone_files} standalone."
    )
    if not offer_content_scan or not knowledge_bases:
        return
    if not typer.confirm("Select a knowledge base and start a content scan now?", default=False):
        typer.echo("No OpenWebUI content scan was started.")
        return
    for index, knowledge_base in enumerate(knowledge_bases, start=1):
        typer.echo(f"  {index}. {knowledge_base.name}")
    selected_index = int(
        _prompt_choice(
            "Knowledge base to scan",
            {str(index) for index in range(1, len(knowledge_bases) + 1)},
            default="1",
        )
    )
    if not typer.confirm(
        "I explicitly consent to retrieving accessible document content for this scan.",
        default=False,
    ):
        typer.echo("OpenWebUI content scan was not started because consent was not granted.")
        return
    _guided_openwebui_content_scan(
        selected,
        knowledge_bases[selected_index - 1].id,
        str(api_key),
    )


def _guided_local_source_scan() -> None:
    local_candidates = discover_local_sources(Path.cwd(), include_root=True)
    default_path = str(local_candidates[0].path) if local_candidates else "."
    if local_candidates:
        typer.echo("Local scan suggestions (file extensions only; not verified as RAG data):")
        for local_candidate in local_candidates[:5]:
            typer.echo(
                f"- {local_candidate.path} ({local_candidate.supported_file_count} supported files)"
            )
    value = typer.prompt("File or folder to scan", default=default_path)
    path = Path(value).expanduser()
    if not path.exists():
        raise typer.BadParameter(f"path not found: {path}")
    _run_guided_local_scan(path)
    typer.echo(f"The report is available in the local dashboard: {dashboard_url()}/reports")


def _guided_onboarding() -> None:
    typer.echo("Welcome to RAGScanner.")
    typer.echo("What would you like to scan?")
    typer.echo("  1. A local file or folder")
    typer.echo("  2. An OpenWebUI knowledge base (API)")
    typer.echo("  3. Exit")
    choice = _prompt_choice("Your choice", {"1", "2", "3"}, default="1")
    if choice == "3":
        typer.echo("No action was taken.")
        return
    if choice == "1":
        _guided_local_source_scan()
        return
    typer.echo("RAGScanner requires separate consent before accessing document content.")
    service_candidates = []
    if typer.confirm("Inspect local OpenWebUI API services?"):
        service_candidates = discover_openwebui_services(include_container_runtimes=True)
        if service_candidates:
            typer.echo("Available OpenWebUI API services:")
            for service_candidate in service_candidates:
                origin = f" via {service_candidate.runtime}" if service_candidate.runtime else ""
                typer.echo(
                    f"- {service_candidate.base_url} "
                    f"({service_candidate.health_path} responded{origin})"
                )
        else:
            typer.echo("No responsive local OpenWebUI API service was found.")
    _guided_openwebui_metadata(service_candidates, offer_content_scan=True)
    typer.echo(
        "Metadata inventory does not retrieve document content unless you explicitly select "
        "and consent to an in-session scan."
    )


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


@app.command("paths")
def show_paths() -> None:
    """Show the platform-native locations used for RAGScanner-owned data."""
    data_dir = get_settings().data_dir.expanduser().resolve()
    typer.echo(f"Data directory: {data_dir}")
    typer.echo(f"Reports directory: {reports_directory(data_dir)}")
    typer.echo(f"History database: {data_dir / 'history.sqlite3'}")
    typer.echo(f"Agent registration: {platform_autostart_path(data_dir)}")
    typer.echo(f"Local dashboard: {dashboard_url()}")


@app.command()
def update() -> None:
    """Upgrade the installed RAGScanner tool; local data and reports are preserved."""
    typer.echo("Updating RAGScanner through uv...")
    _run_uv_tool("upgrade", "ragscanner")
    typer.echo("RAGScanner update completed. Restart the Agent to use the new version immediately.")


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
    purge_data: Annotated[
        bool,
        typer.Option(
            "--purge-data", help="Also permanently delete RAGScanner reports and local history."
        ),
    ] = False,
) -> None:
    """Remove the tool and its autostart record; data is preserved unless explicitly purged."""
    if not yes and not typer.confirm("Uninstall RAGScanner from this user account?"):
        typer.echo("Uninstall cancelled. No changes were made.")
        return
    data_dir = get_settings().data_dir.expanduser().resolve()
    remove_autostart(data_dir)
    if purge_data:
        if not yes and not typer.confirm(f"Permanently delete all RAGScanner data in {data_dir}?"):
            typer.echo("Application removed; local data was preserved.")
        else:
            shutil.rmtree(data_dir, ignore_errors=True)
            typer.echo("RAGScanner local data was permanently deleted.")
    if sys.platform == "win32":
        try:
            _schedule_windows_uninstall(_uv_executable())
        except OSError as error:
            raise typer.BadParameter(f"cannot schedule Windows uninstall: {error}") from error
        typer.echo("RAGScanner uninstall is scheduled after this command exits.")
        return
    typer.echo("Uninstalling RAGScanner through uv...")
    _run_uv_tool("uninstall", "ragscanner")
    typer.echo("RAGScanner uninstall completed.")


@agent_app.command("install")
def agent_install() -> None:
    """Start RAGScanner automatically for the current user after sign-in."""
    data_dir = get_settings().data_dir.expanduser().resolve()
    try:
        registration = install_autostart(data_dir)
    except OSError as error:
        raise typer.BadParameter(f"cannot install the local Agent: {error}") from error
    typer.echo(f"RAGScanner Agent installed for this user: {registration}")
    typer.echo("Dashboard: http://127.0.0.1:8000")


@agent_app.command("uninstall")
def agent_uninstall() -> None:
    """Stop the local Agent and remove its per-user autostart registration."""
    remove_autostart(get_settings().data_dir.expanduser().resolve())
    typer.echo("RAGScanner Agent autostart was removed. Local reports and history were preserved.")


@agent_app.command("status")
def agent_status() -> None:
    """Show the local Agent registration without contacting any remote service."""
    registration = platform_autostart_path(get_settings().data_dir.expanduser().resolve())
    state = "installed" if registration.exists() else "not installed"
    typer.echo(f"Agent autostart: {state}")
    typer.echo(f"Registration: {registration}")
    typer.echo("Dashboard address: http://127.0.0.1:8000")


@agent_app.command("run")
def agent_run(
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    history_db: Annotated[Path | None, typer.Option("--history-db", dir_okay=False)] = None,
    poll_interval: Annotated[float, typer.Option("--poll-interval", min=0.1, max=60)] = 1,
) -> None:
    """Run the local dashboard and durable worker in one foreground Agent process."""
    database = _history_database(history_db)
    typer.echo(f"RAGScanner Agent listening at http://127.0.0.1:{port}", err=True)
    run_agent(database, port=port, poll_interval=poll_interval)


@site_app.command("status")
def site_status() -> None:
    """Show whether this machine maps the dashboard name to loopback."""
    path = hosts_file_path()
    state = "registered" if local_hostname_is_registered(path) else "not registered"
    typer.echo(f"Local hostname: {state}")
    typer.echo(f"Hosts file: {path}")
    typer.echo(f"Dashboard address: {dashboard_url()}")


@site_app.command("register")
def site_register(
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip the hosts-file confirmation.")
    ] = False,
) -> None:
    """Map local.ragscanner.com to 127.0.0.1 on this machine only."""
    path = hosts_file_path()
    if not yes and not typer.confirm(
        f"Add a machine-local loopback mapping for {dashboard_url()} in {path}?"
    ):
        typer.echo("Local hostname registration cancelled. No changes were made.")
        return
    try:
        register_local_hostname(path)
    except PermissionError as error:
        raise typer.BadParameter(
            "administrator permission is required to update the hosts file; rerun this command "
            "from an elevated terminal"
        ) from error
    except OSError as error:
        raise typer.BadParameter(f"cannot update the hosts file: {error}") from error
    typer.echo(f"Local dashboard hostname registered: {dashboard_url()}")


@site_app.command("unregister")
def site_unregister(
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip the hosts-file confirmation.")
    ] = False,
) -> None:
    """Remove only RAGScanner's machine-local hosts-file mapping."""
    path = hosts_file_path()
    if not local_hostname_is_registered(path):
        typer.echo("Local dashboard hostname is not registered.")
        return
    if not yes and not typer.confirm(f"Remove RAGScanner's local mapping from {path}?"):
        typer.echo("Local hostname removal cancelled. No changes were made.")
        return
    try:
        unregister_local_hostname(path)
    except PermissionError as error:
        raise typer.BadParameter(
            "administrator permission is required to update the hosts file; rerun this command "
            "from an elevated terminal"
        ) from error
    except OSError as error:
        raise typer.BadParameter(f"cannot update the hosts file: {error}") from error
    typer.echo("Local dashboard hostname removed.")


@host_app.command("install")
def host_install(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")] = False,
) -> None:
    """Install the always-on machine-local Host Service and loopback dashboard name."""
    if not is_elevated():
        raise typer.BadParameter(
            "machine-wide setup requires administrator permission; open an elevated terminal and run "
            "`ragscanner host install --yes`"
        )
    hosts_path = hosts_file_path()
    if not yes and not typer.confirm(
        f"Install the machine-local Host Service and map {dashboard_url()} to loopback?"
    ):
        typer.echo("Host Service installation cancelled. No changes were made.")
        return
    try:
        register_local_hostname(hosts_path)
        definition = install_host_service()
    except OSError as error:
        raise typer.BadParameter(f"cannot install the Host Service: {error}") from error
    typer.echo("RAGScanner Host Service installed and started.")
    typer.echo(f"Service data: {system_data_dir()}")
    typer.echo(f"Service definition: {definition}")
    typer.echo(f"Dashboard: {dashboard_url()}")


@host_app.command("status")
def host_status() -> None:
    """Show machine-local Host Service locations without changing the machine."""
    typer.echo(f"Administrator terminal: {'yes' if is_elevated() else 'no'}")
    typer.echo(f"Service data: {system_data_dir()}")
    typer.echo(f"Service definition: {service_definition_path()}")
    hostname = "registered" if local_hostname_is_registered(hosts_file_path()) else "not registered"
    typer.echo(f"Local hostname: {hostname}")
    typer.echo(f"Dashboard: {dashboard_url()}")


@host_app.command("uninstall")
def host_uninstall(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")] = False,
) -> None:
    """Stop and remove the Host Service while preserving reports and history."""
    if not is_elevated():
        raise typer.BadParameter(
            "machine-wide setup requires administrator permission; open an elevated terminal and run "
            "`ragscanner host uninstall --yes`"
        )
    if not yes and not typer.confirm("Stop and remove the RAGScanner Host Service?"):
        typer.echo("Host Service removal cancelled. No changes were made.")
        return
    try:
        remove_host_service()
        unregister_local_hostname(hosts_file_path())
    except OSError as error:
        raise typer.BadParameter(f"cannot remove the Host Service: {error}") from error
    typer.echo(
        "RAGScanner Host Service and local hostname mapping were removed. Data was preserved."
    )


@host_app.command("run")
def host_run(
    data_dir: Annotated[Path | None, typer.Option("--data-dir", file_okay=False)] = None,
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    poll_interval: Annotated[float, typer.Option("--poll-interval", min=0.1, max=60)] = 1,
) -> None:
    """Run the Host Service in the foreground; used only by a service manager."""
    selected_data_dir = (data_dir or system_data_dir()).expanduser().resolve()
    selected_data_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"RAGScanner Host Service listening at {dashboard_url(port=port)}", err=True)
    run_agent(
        selected_data_dir / "history.sqlite3",
        port=port,
        poll_interval=poll_interval,
        local_administrator_data_dir=selected_data_dir,
    )


@app.command("setup")
def setup(
    mode: Annotated[str | None, typer.Option("--mode", help="dashboard or terminal")] = None,
) -> None:
    """Choose the initial local setup experience."""
    selected = mode
    if selected is None:
        typer.echo("How would you like to complete RAGScanner setup?")
        typer.echo("  1. Open the local dashboard")
        typer.echo("  2. Continue in this terminal")
        typer.echo("  3. Exit")
        choice = typer.prompt("Your choice", default="1").strip()
        selected = {"1": "dashboard", "2": "terminal", "3": "exit"}.get(choice, "")
    if selected == "exit":
        typer.echo("No setup changes were made.")
        return
    if selected == "dashboard":
        url = dashboard_url()
        typer.echo(
            f"Open {url} after running `ragscanner site register` from an elevated terminal."
        )
        webbrowser.open(url)
        return
    if selected == "terminal":
        typer.echo("Choose your first source:")
        typer.echo("  1. OpenWebUI")
        typer.echo("  2. Another RAG environment")
        typer.echo("  3. Temporary file or folder scan")
        source_choice = _prompt_choice("Your choice", {"1", "2", "3"}, default="1")
        if source_choice == "3":
            _guided_local_source_scan()
            return
        environments = discover_local_rag_environments(
            include_container_runtimes=True, include_kubernetes=True
        )
        matching = [
            item for item in environments if source_choice != "1" or item.platform == "openwebui"
        ]
        if matching:
            typer.echo("Discovered local environments:")
            for index, item in enumerate(matching, start=1):
                typer.echo(
                    f"  {index}. {item.platform} at {item.base_url} "
                    f"({item.discovery_status} via {item.runtime or 'localhost'})"
                )
            choice = int(
                _prompt_choice(
                    "Environment",
                    {str(index) for index in range(1, len(matching) + 1)},
                    default="1",
                )
            )
            selected_environment = matching[choice - 1]
            kind = selected_environment.platform
            location = selected_environment.base_url
            origin = selected_environment.runtime or "localhost"
        else:
            typer.echo("No matching local environment was found. Enter one manually.")
            kind = "openwebui" if source_choice == "1" else "generic"
            location = str(typer.prompt("Service URL")).strip()
            origin = "manual"
        name = str(typer.prompt("Source name", default=kind)).strip()
        credential_ref = None
        if kind == "openwebui":
            value = str(
                typer.prompt(
                    "Credential reference (leave empty to configure later)",
                    default="",
                    show_default=False,
                )
            ).strip()
            credential_ref = value or None
        repository = SQLiteSourceProfileRepository(_history_database(None))
        try:
            repository.set_setting("interface_mode", "cli")
            repository.set_setting(
                "initial_source_mode", "openwebui" if source_choice == "1" else "environment"
            )
            repository.save(
                SourceProfile(
                    name=name,
                    kind=kind
                    if kind in {"openwebui", "qdrant", "chroma", "weaviate", "milvus", "pgvector"}
                    else "generic",
                    base_url=location,
                    credential_ref=credential_ref,
                    discovery_origin=origin,
                    capability_status=(
                        "scan_ready"
                        if kind == "openwebui"
                        and selected_environment.discovery_status == "reachable"
                        else "metadata_only"
                    )
                    if matching
                    else ("scan_ready" if kind == "openwebui" else "metadata_only"),
                )
            )
        finally:
            repository.close()
        typer.echo("Source profile saved. Use `ragscanner host install` for continuous jobs.")
        return
    raise typer.BadParameter("mode must be dashboard or terminal")


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


@app.command("analyze-report")
def analyze_report_command(
    report_file: Annotated[Path, typer.Argument(exists=True, readable=True, dir_okay=False)],
    model: Annotated[str, typer.Option("--model")],
    output: Annotated[Path, typer.Option("--output")],
    provider: Annotated[str, typer.Option("--provider")] = "ollama",
    base_url: Annotated[str, typer.Option("--base-url")] = "http://127.0.0.1:11434",
    credential_ref: Annotated[str | None, typer.Option("--credential-ref")] = None,
    consent_remote: Annotated[bool, typer.Option("--consent-remote")] = False,
) -> None:
    """Create a detailed JSON or HTML report with optional, validated AI analysis."""
    if output.suffix.casefold() not in {".json", ".html", ".htm"}:
        raise typer.BadParameter("output must end in .json, .html, or .htm")
    try:
        report = ReportDocument.model_validate_json(report_file.read_text(encoding="utf-8"))
        adapter: OllamaAnalysisProvider | OpenAICompatibleAnalysisProvider
        if provider == "ollama":
            adapter = OllamaAnalysisProvider(
                base_url=base_url, model=model, consent_remote=consent_remote
            )
        elif provider == "openai-compatible":
            if credential_ref is None:
                raise ValueError("--credential-ref is required for openai-compatible providers")
            adapter = OpenAICompatibleAnalysisProvider(
                base_url=base_url,
                model=model,
                consent_remote=consent_remote,
                api_key=resolve_secret_reference(credential_ref),
            )
        else:
            raise ValueError("provider must be ollama or openai-compatible")
        analysis = asyncio.run(adapter.analyze(build_analysis_request(report)))
        enriched = report.model_copy(update={"ai_analysis": analysis})
        rendered = (
            JsonReporter().render(enriched)
            if output.suffix.casefold() == ".json"
            else HtmlReporter().render(enriched)
        )
        output.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, ModelProviderError) as error:
        raise typer.BadParameter(f"cannot enrich report: {error}") from error
    typer.echo(f"Detailed report written: {output}")


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
