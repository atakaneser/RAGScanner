"""Jinja dashboard routes composed over application services."""

import hashlib
import hmac
import os
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.application import (
    DurableWorker,
    HistoryApplicationService,
    HistoryNotFoundError,
    JobApplicationService,
    StaticScanApplicationService,
    StaticScanJobHandler,
    StaticScanJobPayload,
    resolve_secret_reference,
)
from ragscanner.jobs import JobKind, JobNotFoundError, JobRecord, JobStateError, JobStatus
from ragscanner.local_auth import LocalAdministratorStore
from ragscanner.onboarding import (
    OpenWebUIDiscoveryError,
    discover_openwebui_knowledge_bases,
    discover_openwebui_services,
)
from ragscanner.providers import PROVIDER_CATALOG, ModelProviderError, discover_provider_models
from ragscanner.quality import RAGConfigurationConfig, RAGProfile
from ragscanner.reporting import ReportExportFormat, export_report, report_export_filename
from ragscanner.storage import (
    ENV_CREDENTIAL_REFERENCE_ERROR,
    DashboardSettings,
    DuplicateSourceError,
    MachineSecretStore,
    ScanScheduleRequest,
    SourceProfile,
    SQLiteJobRepository,
    SQLiteScanHistoryRepository,
    SQLiteScheduleRepository,
    SQLiteSourceProfileRepository,
    normalize_env_credential_reference,
)

DASHBOARD_ASSET_ROOT = Path(__file__).with_name("templates")
SCANNABLE_SOURCE_KINDS = frozenset({"filesystem", "openwebui", "website", "sharepoint"})
templates = Jinja2Templates(directory=DASHBOARD_ASSET_ROOT)


def _dashboard_asset_version() -> str:
    digest = hashlib.sha256()
    for name in ("dashboard.css", "dashboard-i18n.js", "dashboard.js"):
        digest.update((DASHBOARD_ASSET_ROOT / name).read_bytes())
    return digest.hexdigest()[:12]


templates.env.globals["asset_version"] = _dashboard_asset_version()


def _display_timestamp(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone().strftime("%Y-%m-%d %H:%M %Z")


templates.env.filters["display_timestamp"] = _display_timestamp


def _score_band(value: float | None) -> str:
    if value is None:
        return "unassessed"
    if value < 55:
        return "critical"
    if value < 70:
        return "poor"
    if value < 85:
        return "warning"
    return "healthy"


templates.env.filters["score_band"] = _score_band


def _rag_config(
    profile: str,
    embedding_context_tokens: int | None,
    generator_context_tokens: int | None,
    retrieval_top_k: int | None,
) -> RAGConfigurationConfig:
    return RAGConfigurationConfig(
        profile=RAGProfile(profile),
        embedding_context_tokens=embedding_context_tokens,
        generator_context_tokens=generator_context_tokens,
        retrieval_top_k=retrieval_top_k,
    )


def _source_secret_reference(profile_id: str) -> str:
    return f"source-{profile_id}"


def _ai_secret_reference() -> str:
    return f"ai-{secrets.token_hex(12)}"


def _store_secret(database_path: Path, secret_id: str, value: str) -> str:
    """Store a dashboard credential outside SQLite with owner-only permissions."""

    return MachineSecretStore(database_path.parent).save(secret_id, value)


def _effective_source_profile(
    profile: SourceProfile,
    *,
    repository: SQLiteSourceProfileRepository | None = None,
    secret_store: MachineSecretStore | None = None,
) -> SourceProfile:
    if profile.kind in {"filesystem", "website", "sharepoint"}:
        status = "scan_ready"
    elif profile.kind not in SCANNABLE_SOURCE_KINDS:
        status = "metadata_only"
    else:
        try:
            if not profile.credential_ref:
                raise ValueError("missing credential")
            resolve_secret_reference(profile.credential_ref)
        except ValueError:
            rebound = secret_store.rebind(profile.credential_ref) if secret_store else None
            if rebound:
                try:
                    resolve_secret_reference(rebound)
                except ValueError:
                    status = "connection_required"
                else:
                    profile = profile.model_copy(update={"credential_ref": rebound})
                    if repository is not None:
                        repository.save(profile)
                    status = "scan_ready"
            else:
                status = "connection_required"
        else:
            status = "scan_ready"
    return profile.model_copy(update={"capability_status": status})


def _ai_config(
    enabled: bool,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    credential_ref: str | None,
    remote_consent: bool,
    api_key: str | None = None,
    *,
    database_path: Path | None = None,
    defaults: DashboardSettings | None = None,
    output_language: str = "en",
) -> AIProviderConfig:
    if defaults is not None:
        provider = provider or defaults.ai_provider
        model = model or defaults.ai_model
        base_url = base_url or defaults.ai_base_url
        credential_ref = credential_ref or defaults.ai_credential_ref
        remote_consent = remote_consent or defaults.ai_remote_consent
    secret = api_key.strip() if api_key else ""
    reference = credential_ref.strip() if credential_ref else None
    if reference and not reference.startswith("file-secret:"):
        reference = normalize_env_credential_reference(reference)
    if secret:
        if database_path is None:
            raise ValueError("machine data path is required for a direct API key")
        reference = _store_secret(database_path, _ai_secret_reference(), secret)
    try:
        return AIProviderConfig(
            enabled=enabled,
            provider=provider.strip() if provider else None,
            model=model.strip() if model else None,
            base_url=base_url.strip() if base_url else None,
            credential_ref=reference,
            remote_consent=remote_consent,
            output_language=output_language,
        )
    except ValueError:
        if secret and reference and database_path is not None:
            MachineSecretStore(database_path.parent).delete(reference)
        raise


def _request_locale(request: Request, settings: DashboardSettings | None = None) -> str:
    locale = request.cookies.get("ragscanner_locale") or (settings.locale if settings else "en")
    return locale if locale in {"en", "tr", "de", "fr", "zh-CN", "it"} else "en"


def _optional_schedule_time(value: str | None) -> datetime | None:
    """Parse a browser-supplied ISO timestamp while keeping legacy submissions valid."""

    if not value or not value.strip():
        return None
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("schedule start time must include a timezone")
    return parsed.astimezone(UTC)


def _dashboard_settings(database_path: Path) -> DashboardSettings:
    repository = SQLiteSourceProfileRepository(database_path)
    try:
        return repository.dashboard_settings()
    finally:
        repository.close()


def register_dashboard(
    app: FastAPI,
    database_path: Path,
    *,
    administrator_store: LocalAdministratorStore | None = None,
) -> None:
    """Register localhost-only HTML routes without exposing API credentials to the browser."""

    @app.middleware("http")
    async def local_dashboard_login(request: Request, call_next):  # type: ignore[no-untyped-def]
        if administrator_store is not None and _requires_local_administrator(request):
            session = request.cookies.get("ragscanner_session", "")
            if not administrator_store.configured:
                if request.url.path.startswith("/api/"):
                    return JSONResponse({"error": {"code": "setup_required"}}, status_code=401)
                return RedirectResponse("/setup", status_code=303)
            if not administrator_store.valid_session(session):
                if request.url.path.startswith("/api/"):
                    return JSONResponse(
                        {"error": {"code": "local_administrator_required"}}, status_code=401
                    )
                return RedirectResponse("/login", status_code=303)
        return await call_next(request)

    @app.get("/setup", response_class=HTMLResponse, response_model=None, include_in_schema=False)
    async def setup_dashboard(request: Request) -> HTMLResponse | RedirectResponse:
        if administrator_store is None:
            return RedirectResponse("/", status_code=303)
        if administrator_store.configured:
            return RedirectResponse("/login", status_code=303)
        csrf_token = request.cookies.get("ragscanner_csrf") or secrets.token_urlsafe(32)
        response = templates.TemplateResponse(
            request, "setup.html", {"error": "", "csrf_token": csrf_token}
        )
        _set_csrf_cookie(response, csrf_token)
        return response

    @app.post("/setup/discovery", include_in_schema=False)
    async def setup_discovery(
        request: Request,
        csrf_token: Annotated[str, Form()],
    ) -> JSONResponse:
        _validate_csrf(request, csrf_token)
        return await _openwebui_discovery_response()

    @app.post("/setup", response_class=HTMLResponse, response_model=None, include_in_schema=False)
    async def create_local_administrator(
        request: Request,
        username: Annotated[str, Form(min_length=3, max_length=80)],
        password: Annotated[str, Form(min_length=14, max_length=512)],
        csrf_token: Annotated[str, Form()],
        interface_mode: Annotated[str, Form(pattern=r"^(web|cli)$")] = "web",
        source_mode: Annotated[str, Form(pattern=r"^(openwebui|temporary_folder)$")] = "openwebui",
        source_name: Annotated[str | None, Form(max_length=160)] = None,
        source_location: Annotated[str | None, Form(max_length=4096)] = None,
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        api_key: Annotated[str | None, Form(max_length=4096)] = None,
    ) -> HTMLResponse | RedirectResponse:
        if administrator_store is None:
            return RedirectResponse("/", status_code=303)
        _validate_csrf(request, csrf_token)
        try:
            pending_profile = None
            if source_location and source_mode != "temporary_folder":
                kind = "openwebui"
                pending_profile = SourceProfile(
                    name=(source_name or kind).strip(),
                    kind=kind,
                    base_url=source_location.strip(),
                    credential_ref=None,
                    discovery_origin="setup",
                    capability_status="connection_required",
                )
                normalized_credential_ref = normalize_env_credential_reference(credential_ref)
                if api_key:
                    normalized_credential_ref = _source_secret_reference(pending_profile.id)
                pending_profile = pending_profile.model_copy(
                    update={
                        "credential_ref": normalized_credential_ref,
                        "capability_status": (
                            "scan_ready"
                            if kind == "openwebui" and (api_key or normalized_credential_ref)
                            else pending_profile.capability_status
                        ),
                    }
                )
        except ValueError:
            return templates.TemplateResponse(
                request,
                "setup.html",
                {"error": ENV_CREDENTIAL_REFERENCE_ERROR, "csrf_token": csrf_token},
                status_code=400,
            )
        try:
            administrator_store.create(username, password)
            session = administrator_store.issue_session(username.strip())
            sources = SQLiteSourceProfileRepository(database_path)
            try:
                sources.set_setting("interface_mode", interface_mode)
                sources.set_setting("initial_source_mode", source_mode)
                if pending_profile is not None:
                    if api_key:
                        pending_profile = pending_profile.model_copy(
                            update={
                                "credential_ref": _store_secret(
                                    database_path,
                                    _source_secret_reference(pending_profile.id),
                                    api_key,
                                )
                            }
                        )
                    sources.save(pending_profile)
            finally:
                sources.close()
        except ValueError as error:
            return templates.TemplateResponse(
                request,
                "setup.html",
                {"error": str(error), "csrf_token": csrf_token},
                status_code=400,
            )
        response = RedirectResponse("/", status_code=303)
        _set_session_cookie(response, session)
        return response

    @app.get("/login", response_class=HTMLResponse, response_model=None, include_in_schema=False)
    async def login_dashboard(request: Request) -> HTMLResponse | RedirectResponse:
        if administrator_store is None:
            return RedirectResponse("/", status_code=303)
        if not administrator_store.configured:
            return RedirectResponse("/setup", status_code=303)
        return templates.TemplateResponse(request, "login.html", {"error": ""})

    @app.post("/login", response_class=HTMLResponse, response_model=None, include_in_schema=False)
    async def login_local_administrator(
        request: Request,
        username: Annotated[str, Form(min_length=3, max_length=80)],
        password: Annotated[str, Form(min_length=1, max_length=512)],
    ) -> HTMLResponse | RedirectResponse:
        if administrator_store is None or not administrator_store.verify(
            username.strip(), password
        ):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Username or password is invalid."},
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        _set_session_cookie(response, administrator_store.issue_session(username.strip()))
        return response

    @app.post("/logout", include_in_schema=False)
    async def logout_dashboard() -> RedirectResponse:
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("ragscanner_session")
        return response

    def render_dashboard(
        request: Request,
        *,
        page: str,
        report_id: str | None = None,
        baseline_id: str | None = None,
        candidate_id: str | None = None,
    ) -> HTMLResponse:
        jobs_repository = SQLiteJobRepository(database_path)
        history_repository = SQLiteScanHistoryRepository(database_path)
        source_repository = SQLiteSourceProfileRepository(database_path)
        schedule_repository = SQLiteScheduleRepository(database_path)
        try:
            settings = source_repository.dashboard_settings()
            jobs = JobApplicationService(jobs_repository).list(limit=settings.rows_per_page)
            history_service = HistoryApplicationService(history_repository)
            date_from, date_to = _date_filters(request)
            selected_source = request.query_params.get("source") or None
            history = history_service.list(
                limit=settings.rows_per_page,
                created_after=date_from,
                created_before=date_to,
                source=selected_source,
            )
            all_history = history_service.list(limit=200)
            latest_report = (
                history_service.get(all_history.items[0].history_id) if all_history.items else None
            )
            previous_report = (
                history_service.get(all_history.items[1].history_id)
                if len(all_history.items) > 1
                else None
            )
            selected_report = history_service.get(report_id) if report_id else None
            comparison = (
                history_service.compare(baseline_id, candidate_id)
                if baseline_id and candidate_id
                else None
            )
            secret_store = MachineSecretStore(database_path.parent)
            profiles = [
                _effective_source_profile(
                    profile,
                    repository=source_repository,
                    secret_store=secret_store,
                )
                for profile in source_repository.list()
            ]
            job_profiles = [
                profile for profile in profiles if profile.kind in SCANNABLE_SOURCE_KINDS
            ]
            schedules = schedule_repository.list(limit=settings.rows_per_page)
            job_logs = [_job_log(job, history_repository) for job in jobs.items]
        finally:
            schedule_repository.close()
            source_repository.close()
            history_repository.close()
            jobs_repository.close()
        csrf_token = request.cookies.get("ragscanner_csrf") or secrets.token_urlsafe(32)
        coverage = _coverage(latest_report.assessment_coverage if latest_report else {})
        latest_score = all_history.items[0].overall_score if all_history.items else None
        previous_score = all_history.items[1].overall_score if len(all_history.items) > 1 else None
        score_delta = (
            round(latest_score - previous_score, 1)
            if latest_score is not None and previous_score is not None
            else None
        )
        selected_report_summary = next(
            (item for item in all_history.items if item.history_id == report_id), None
        )
        regular_findings = (
            [
                finding
                for finding in selected_report.findings
                if not finding.metadata.get("group_id")
            ]
            if selected_report
            else []
        )
        response = templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "jobs": jobs.items,
                "job_total": jobs.total,
                "job_logs": job_logs,
                "scans": history.items,
                "scan_total": history.total,
                "all_scans": all_history.items,
                "latest": all_history.items[0] if all_history.items else None,
                "coverage": coverage,
                "latest_report": latest_report,
                "previous_report": previous_report,
                "score_delta": score_delta,
                "page": page,
                "profiles": profiles,
                "job_profiles": job_profiles,
                "schedules": schedules,
                "selected_report": selected_report,
                "regular_findings": regular_findings,
                "selected_report_summary": selected_report_summary,
                "selected_report_id": report_id,
                "comparison": comparison,
                "baseline_id": baseline_id,
                "candidate_id": candidate_id,
                "csrf_token": csrf_token,
                "request_id": secrets.token_hex(16),
                "notice": request.query_params.get("notice", ""),
                "host_auth_enabled": administrator_store is not None,
                "ai_providers": PROVIDER_CATALOG,
                "settings": settings,
                "locale": _request_locale(request, settings),
            },
        )
        _set_csrf_cookie(response, csrf_token)
        return response

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request) -> HTMLResponse:
        return render_dashboard(request, page="overview")

    @app.get("/sources", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_sources(request: Request) -> HTMLResponse:
        return render_dashboard(request, page="sources")

    @app.get("/jobs", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_jobs(request: Request) -> HTMLResponse:
        return render_dashboard(request, page="jobs")

    @app.get("/reports", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_reports(request: Request) -> HTMLResponse:
        return render_dashboard(request, page="reports")

    @app.get("/reports/{history_id}", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_report_detail(request: Request, history_id: str) -> HTMLResponse:
        return render_dashboard(request, page="report_detail", report_id=history_id)

    @app.get("/reports/{history_id}/download/{export_format}", include_in_schema=False)
    async def dashboard_download_report(
        request: Request,
        history_id: str,
        export_format: ReportExportFormat,
    ) -> Response:
        history_repository = SQLiteScanHistoryRepository(database_path)
        source_repository = SQLiteSourceProfileRepository(database_path)
        try:
            report = HistoryApplicationService(history_repository).get(history_id)
            locale = _request_locale(request, source_repository.dashboard_settings())
        finally:
            source_repository.close()
            history_repository.close()
        exported = await run_in_threadpool(export_report, report, export_format, locale=locale)
        filename = report_export_filename(report, history_id, exported.extension)
        return Response(
            content=exported.content,
            media_type=exported.media_type,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post("/dashboard/reports/{history_id}/delete", include_in_schema=False)
    async def dashboard_delete_report(
        request: Request,
        history_id: str,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteScanHistoryRepository(database_path)
        try:
            HistoryApplicationService(repository).delete(history_id)
        except HistoryNotFoundError:
            return RedirectResponse("/reports?notice=report-not-found", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/reports?notice=report-deleted", status_code=303)

    @app.get("/compare", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_compare(
        request: Request,
        baseline: str,
        candidate: str,
    ) -> HTMLResponse:
        return render_dashboard(
            request, page="compare", baseline_id=baseline, candidate_id=candidate
        )

    @app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_settings(request: Request) -> HTMLResponse:
        return render_dashboard(request, page="settings")

    @app.post("/dashboard/settings", include_in_schema=False)
    async def dashboard_save_settings(
        request: Request,
        csrf_token: Annotated[str, Form()],
        locale: Annotated[str, Form(pattern=r"^(en|tr|de|fr|zh-CN|it)$")],
        timezone: Annotated[str, Form(pattern=r"^(local|UTC)$")],
        report_detail: Annotated[str, Form(pattern=r"^(standard|detailed)$")],
        rows_per_page: Annotated[int, Form(ge=10, le=100)],
        ai_provider: Annotated[str, Form(max_length=80)],
        ai_model: Annotated[str, Form(max_length=240)],
        ai_base_url: Annotated[str, Form(max_length=2048)],
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        reduced_motion: Annotated[bool, Form()] = False,
        show_absolute_paths: Annotated[bool, Form()] = False,
        ai_remote_consent: Annotated[bool, Form()] = False,
        remove_ai_credential: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteSourceProfileRepository(database_path)
        secret_store = MachineSecretStore(database_path.parent)
        try:
            previous = repository.dashboard_settings()
            reference = previous.ai_credential_ref
            if remove_ai_credential:
                secret_store.delete(reference)
                reference = None
            elif ai_api_key:
                secret_store.delete(reference)
                reference = secret_store.save("ai-default", ai_api_key)
            elif ai_credential_ref:
                replacement = normalize_env_credential_reference(ai_credential_ref)
                secret_store.delete(reference)
                reference = replacement
            settings = DashboardSettings(
                locale=locale,
                timezone=timezone,
                report_detail=report_detail,
                rows_per_page=rows_per_page,
                reduced_motion=reduced_motion,
                show_absolute_paths=show_absolute_paths,
                ai_provider=ai_provider,
                ai_model=ai_model,
                ai_base_url=ai_base_url,
                ai_credential_ref=reference,
                ai_remote_consent=ai_remote_consent,
            )
            repository.save_dashboard_settings(settings)
        except ValueError:
            return RedirectResponse("/settings?notice=invalid-settings", status_code=303)
        finally:
            repository.close()
        response = RedirectResponse("/settings?notice=settings-saved", status_code=303)
        response.set_cookie(
            "ragscanner_locale", locale, samesite="strict", secure=False, max_age=365 * 86400
        )
        return response

    @app.post("/dashboard/password", include_in_schema=False)
    async def dashboard_change_password(
        request: Request,
        csrf_token: Annotated[str, Form()],
        current_password: Annotated[str, Form(min_length=1, max_length=512)],
        new_password: Annotated[str, Form(min_length=1, max_length=512)],
        confirm_password: Annotated[str, Form(min_length=1, max_length=512)],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        if administrator_store is None:
            return RedirectResponse("/settings?notice=password-unavailable", status_code=303)
        if new_password != confirm_password:
            return RedirectResponse("/settings?notice=password-mismatch", status_code=303)
        try:
            administrator = administrator_store.change_password(current_password, new_password)
        except PermissionError:
            return RedirectResponse("/settings?notice=password-current-invalid", status_code=303)
        except ValueError as error:
            notice = "password-reused" if "must differ" in str(error) else "password-invalid"
            return RedirectResponse(f"/settings?notice={notice}", status_code=303)
        response = RedirectResponse("/settings?notice=password-changed", status_code=303)
        _set_session_cookie(response, administrator_store.issue_session(administrator.username))
        return response

    @app.post("/dashboard/sources", include_in_schema=False)
    async def dashboard_add_source(
        request: Request,
        csrf_token: Annotated[str, Form()],
        name: Annotated[str, Form(min_length=1, max_length=160)],
        kind: Annotated[
            str,
            Form(pattern=r"^(openwebui|filesystem|website|sharepoint)$"),
        ],
        location: Annotated[str, Form(min_length=1, max_length=4096)],
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        api_key: Annotated[str | None, Form(max_length=4096)] = None,
        discovery_origin: Annotated[str, Form(max_length=80)] = "manual",
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteSourceProfileRepository(database_path)
        stored_reference: str | None = None
        try:
            profile = SourceProfile(
                name=name.strip(),
                kind=kind,
                local_path=location.strip() if kind == "filesystem" else None,
                base_url=None if kind == "filesystem" else location.strip(),
                credential_ref=None,
                discovery_origin=discovery_origin,
                capability_status=(
                    "scan_ready"
                    if kind in {"filesystem", "website", "sharepoint"}
                    else "connection_required"
                ),
            )
            normalized_reference = normalize_env_credential_reference(credential_ref)
            if api_key:
                normalized_reference = _store_secret(
                    database_path, _source_secret_reference(profile.id), api_key
                )
                stored_reference = normalized_reference
            profile = profile.model_copy(
                update={
                    "credential_ref": normalized_reference,
                    "capability_status": (
                        "scan_ready"
                        if kind in {"website", "sharepoint"}
                        or (kind == "openwebui" and (api_key or normalized_reference))
                        else profile.capability_status
                    ),
                }
            )
            repository.save(profile)
        except DuplicateSourceError:
            MachineSecretStore(database_path.parent).delete(stored_reference)
            return RedirectResponse("/sources?notice=source-exists", status_code=303)
        except ValueError:
            MachineSecretStore(database_path.parent).delete(stored_reference)
            return RedirectResponse("/sources?notice=invalid-source", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/sources?notice=source-saved", status_code=303)

    @app.post("/dashboard/sources/{profile_id}/connect", include_in_schema=False)
    async def dashboard_connect_source(
        request: Request,
        profile_id: str,
        csrf_token: Annotated[str, Form()],
        api_key: Annotated[str | None, Form(max_length=4096)] = None,
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
    ) -> JSONResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteSourceProfileRepository(database_path)
        try:
            profile = repository.get(profile_id)
            if profile is None:
                return JSONResponse(
                    {"error": "The selected source no longer exists."}, status_code=404
                )
            if profile.kind != "openwebui" or not profile.base_url:
                return JSONResponse(
                    {
                        "error": "This source can be inventoried, but its content connector is not available yet."
                    },
                    status_code=400,
                )
            if api_key:
                resolved = api_key.strip()
                reference = None
            else:
                reference = normalize_env_credential_reference(credential_ref)
                resolved = resolve_secret_reference(reference) if reference else ""
            if not resolved:
                return JSONResponse({"error": "Enter an API key to continue."}, status_code=400)
            knowledge_bases = await run_in_threadpool(
                lambda: discover_openwebui_knowledge_bases(profile.base_url or "", resolved)
            )
            if api_key:
                reference = _store_secret(
                    database_path, _source_secret_reference(profile.id), api_key
                )
            assert reference is not None
            repository.save(
                profile.model_copy(
                    update={"credential_ref": reference, "capability_status": "scan_ready"}
                )
            )
        except (OpenWebUIDiscoveryError, ValueError):
            return JSONResponse(
                {"error": "The API key or OpenWebUI address could not be verified."},
                status_code=400,
            )
        finally:
            repository.close()
        return JSONResponse(
            {
                "status": "scan_ready",
                "credential_ref": reference,
                "knowledge_bases": [
                    {"id": item.id, "name": item.name, "description": item.description}
                    for item in knowledge_bases
                ],
            }
        )

    @app.post("/dashboard/sources/{profile_id}/delete", include_in_schema=False)
    async def dashboard_delete_source(
        request: Request,
        profile_id: str,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteSourceProfileRepository(database_path)
        try:
            profile = repository.get(profile_id)
            repository.delete(profile_id)
            if profile is not None:
                MachineSecretStore(database_path.parent).delete(profile.credential_ref)
        finally:
            repository.close()
        return RedirectResponse("/sources?notice=source-deleted", status_code=303)

    @app.post("/dashboard/scans/local", include_in_schema=False)
    async def dashboard_local_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        path: Annotated[str, Form(min_length=1, max_length=4096)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        source_name: Annotated[str | None, Form(max_length=160)] = None,
        execution_mode: Annotated[str, Form(pattern=r"^(one_time|scheduled)$")] = "one_time",
        schedule_name: Annotated[str | None, Form(max_length=160)] = None,
        interval_minutes: Annotated[int, Form(ge=15, le=525600)] = 1440,
        schedule_start_at: Annotated[str | None, Form(max_length=80)] = None,
        scan_consent: Annotated[bool, Form()] = False,
        ai_enabled: Annotated[bool, Form()] = False,
        ai_provider: Annotated[str | None, Form(max_length=80)] = None,
        ai_model: Annotated[str | None, Form(max_length=240)] = None,
        ai_base_url: Annotated[str | None, Form(max_length=2048)] = None,
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        ai_remote_consent: Annotated[bool, Form()] = False,
        rag_profile: Annotated[str, Form(max_length=80)] = "general_qa",
        embedding_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        generator_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        retrieval_top_k: Annotated[int | None, Form(ge=1, le=1000)] = None,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        if not scan_consent:
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        repository = SQLiteJobRepository(database_path)
        created_ai_reference: str | None = None
        try:
            resolved = Path(path).expanduser().resolve(strict=True)
            friendly_name = (source_name or resolved.name).strip()
            selected_settings = _dashboard_settings(database_path)
            ai_config = _ai_config(
                ai_enabled,
                ai_provider,
                ai_model,
                ai_base_url,
                ai_credential_ref,
                ai_remote_consent,
                ai_api_key,
                database_path=database_path,
                defaults=selected_settings,
                output_language=_request_locale(request, selected_settings),
            )
            if ai_api_key:
                created_ai_reference = ai_config.credential_ref
            rag_config = _rag_config(
                rag_profile,
                embedding_context_tokens,
                generator_context_tokens,
                retrieval_top_k,
            )
            if execution_mode == "scheduled":
                schedule_repository = SQLiteScheduleRepository(database_path)
                try:
                    schedule_repository.create(
                        ScanScheduleRequest(
                            name=(schedule_name or friendly_name).strip(),
                            interval_minutes=interval_minutes,
                            next_run_at=_optional_schedule_time(schedule_start_at),
                            payload=StaticScanJobPayload(
                                source_kind="local",
                                execution_mode="scheduled",
                                source_name=friendly_name,
                                path=str(resolved),
                                ai=ai_config,
                                rag=rag_config,
                            ).model_dump(mode="json", exclude_none=True),
                        )
                    )
                finally:
                    schedule_repository.close()
            else:
                JobApplicationService(repository).enqueue_local_scan(
                    resolved,
                    source_name=friendly_name,
                    idempotency_key=idempotency_key,
                    ai_config=ai_config,
                    rag_config=rag_config,
                )
        except (OSError, ValueError, JobStateError):
            MachineSecretStore(database_path.parent).delete(created_ai_reference)
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        notice = "schedule-saved" if execution_mode == "scheduled" else "scan-queued"
        return RedirectResponse(f"/jobs?notice={notice}", status_code=303)

    @app.post("/dashboard/discovery/environments", include_in_schema=False)
    async def dashboard_discover_environments(
        request: Request,
        csrf_token: Annotated[str, Form()],
        metadata_consent: Annotated[bool, Form()] = False,
    ) -> JSONResponse:
        _validate_csrf(request, csrf_token)
        if not metadata_consent:
            return JSONResponse(
                {"error": "Explicit consent is required before local environment discovery."},
                status_code=400,
            )
        return await _openwebui_discovery_response()

    @app.post("/dashboard/discovery/openwebui/knowledge-bases", include_in_schema=False)
    async def dashboard_discover_openwebui_knowledge_bases(
        request: Request,
        csrf_token: Annotated[str, Form()],
        base_url: Annotated[str, Form(min_length=1, max_length=2048)],
        credential_ref: Annotated[str, Form(min_length=1, max_length=500)],
    ) -> JSONResponse:
        _validate_csrf(request, csrf_token)
        try:
            api_key = resolve_secret_reference(credential_ref)
            knowledge_bases = await run_in_threadpool(
                lambda: discover_openwebui_knowledge_bases(base_url, api_key)
            )
        except (OpenWebUIDiscoveryError, ValueError):
            return JSONResponse(
                {"error": "OpenWebUI knowledge-base discovery was unavailable."}, status_code=400
            )
        return JSONResponse(
            {
                "knowledge_bases": [
                    {"id": item.id, "name": item.name, "description": item.description}
                    for item in knowledge_bases
                ]
            }
        )

    @app.post("/dashboard/discovery/ai-models", include_in_schema=False)
    async def dashboard_discover_ai_models(
        request: Request,
        csrf_token: Annotated[str, Form()],
        provider: Annotated[str, Form(max_length=80)],
        base_url: Annotated[str | None, Form(max_length=2048)] = None,
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        api_key: Annotated[str | None, Form(max_length=4096)] = None,
        remote_consent: Annotated[bool, Form()] = False,
    ) -> JSONResponse:
        _validate_csrf(request, csrf_token)
        temporary_credential_ref: str | None = None
        try:
            config = _ai_config(
                True,
                provider,
                "model-inventory",
                base_url,
                credential_ref,
                remote_consent,
                api_key,
                database_path=database_path,
                defaults=_dashboard_settings(database_path),
                output_language=_request_locale(request, _dashboard_settings(database_path)),
            )
            if api_key:
                temporary_credential_ref = config.credential_ref
            models = await discover_provider_models(
                config, secret_resolver=resolve_secret_reference
            )
        except ModelProviderError as error:
            return JSONResponse({"error": error.safe_message, "code": error.code}, status_code=400)
        except (OSError, ValueError):
            return JSONResponse(
                {
                    "error": "The provider configuration or credential is unavailable.",
                    "code": "ai_provider_configuration_invalid",
                },
                status_code=400,
            )
        finally:
            if temporary_credential_ref:
                MachineSecretStore(database_path.parent).delete(temporary_credential_ref)
        return JSONResponse({"models": models})

    @app.post("/dashboard/scans/openwebui", include_in_schema=False)
    async def dashboard_openwebui_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        base_url: Annotated[str, Form(min_length=1, max_length=2048)],
        knowledge_id: Annotated[str, Form(min_length=1, max_length=240)],
        credential_ref: Annotated[str, Form(min_length=1, max_length=500)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        source_name: Annotated[str | None, Form(max_length=160)] = None,
        execution_mode: Annotated[str, Form(pattern=r"^(one_time|scheduled)$")] = "one_time",
        schedule_name: Annotated[str | None, Form(max_length=160)] = None,
        interval_minutes: Annotated[int, Form(ge=15, le=525600)] = 1440,
        schedule_start_at: Annotated[str | None, Form(max_length=80)] = None,
        content_consent: Annotated[bool, Form()] = False,
        ai_enabled: Annotated[bool, Form()] = False,
        ai_provider: Annotated[str | None, Form(max_length=80)] = None,
        ai_model: Annotated[str | None, Form(max_length=240)] = None,
        ai_base_url: Annotated[str | None, Form(max_length=2048)] = None,
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        ai_remote_consent: Annotated[bool, Form()] = False,
        rag_profile: Annotated[str, Form(max_length=80)] = "general_qa",
        embedding_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        generator_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        retrieval_top_k: Annotated[int | None, Form(ge=1, le=1000)] = None,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteJobRepository(database_path)
        created_ai_reference: str | None = None
        try:
            selected_settings = _dashboard_settings(database_path)
            ai_config = _ai_config(
                ai_enabled,
                ai_provider,
                ai_model,
                ai_base_url,
                ai_credential_ref,
                ai_remote_consent,
                ai_api_key,
                database_path=database_path,
                defaults=selected_settings,
                output_language=_request_locale(request, selected_settings),
            )
            if ai_api_key:
                created_ai_reference = ai_config.credential_ref
            rag_config = _rag_config(
                rag_profile,
                embedding_context_tokens,
                generator_context_tokens,
                retrieval_top_k,
            )
            friendly_name = (source_name or f"OpenWebUI · {knowledge_id}").strip()
            if execution_mode == "scheduled":
                schedule_repository = SQLiteScheduleRepository(database_path)
                try:
                    schedule_repository.create(
                        ScanScheduleRequest(
                            name=(schedule_name or friendly_name).strip(),
                            interval_minutes=interval_minutes,
                            next_run_at=_optional_schedule_time(schedule_start_at),
                            payload=StaticScanJobPayload(
                                source_kind="openwebui",
                                execution_mode="scheduled",
                                source_name=friendly_name,
                                openwebui_base_url=base_url,
                                openwebui_knowledge_id=knowledge_id,
                                credential_ref=credential_ref,
                                content_consent=content_consent,
                                ai=ai_config,
                                rag=rag_config,
                            ).model_dump(mode="json", exclude_none=True),
                        )
                    )
                finally:
                    schedule_repository.close()
            else:
                JobApplicationService(repository).enqueue_openwebui_scan(
                    base_url=base_url,
                    knowledge_id=knowledge_id,
                    credential_ref=credential_ref,
                    content_consent=content_consent,
                    source_name=friendly_name,
                    idempotency_key=idempotency_key,
                    ai_config=ai_config,
                    rag_config=rag_config,
                )
        except (ValueError, JobStateError):
            MachineSecretStore(database_path.parent).delete(created_ai_reference)
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        notice = "schedule-saved" if execution_mode == "scheduled" else "scan-queued"
        return RedirectResponse(f"/jobs?notice={notice}", status_code=303)

    @app.post("/dashboard/scans/website", include_in_schema=False)
    async def dashboard_website_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        url: Annotated[str, Form(min_length=1, max_length=4096)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        source_name: Annotated[str | None, Form(max_length=160)] = None,
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        execution_mode: Annotated[str, Form(pattern=r"^(one_time|scheduled)$")] = "one_time",
        schedule_name: Annotated[str | None, Form(max_length=160)] = None,
        interval_minutes: Annotated[int, Form(ge=15, le=525600)] = 1440,
        schedule_start_at: Annotated[str | None, Form(max_length=80)] = None,
        content_consent: Annotated[bool, Form()] = False,
        ai_enabled: Annotated[bool, Form()] = False,
        ai_provider: Annotated[str | None, Form(max_length=80)] = None,
        ai_model: Annotated[str | None, Form(max_length=240)] = None,
        ai_base_url: Annotated[str | None, Form(max_length=2048)] = None,
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        ai_remote_consent: Annotated[bool, Form()] = False,
        rag_profile: Annotated[str, Form(max_length=80)] = "general_qa",
        embedding_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        generator_context_tokens: Annotated[int | None, Form(ge=128)] = None,
        retrieval_top_k: Annotated[int | None, Form(ge=1, le=1000)] = None,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteJobRepository(database_path)
        created_ai_reference: str | None = None
        try:
            selected_settings = _dashboard_settings(database_path)
            ai_config = _ai_config(
                ai_enabled,
                ai_provider,
                ai_model,
                ai_base_url,
                ai_credential_ref,
                ai_remote_consent,
                ai_api_key,
                database_path=database_path,
                defaults=selected_settings,
                output_language=_request_locale(request, selected_settings),
            )
            if ai_api_key:
                created_ai_reference = ai_config.credential_ref
            rag_config = _rag_config(
                rag_profile,
                embedding_context_tokens,
                generator_context_tokens,
                retrieval_top_k,
            )
            normalized_reference = normalize_env_credential_reference(credential_ref)
            friendly_name = (source_name or urlparse(url).hostname or "Website").strip()
            if execution_mode == "scheduled":
                schedule_repository = SQLiteScheduleRepository(database_path)
                try:
                    schedule_repository.create(
                        ScanScheduleRequest(
                            name=(schedule_name or friendly_name).strip(),
                            interval_minutes=interval_minutes,
                            next_run_at=_optional_schedule_time(schedule_start_at),
                            payload=StaticScanJobPayload(
                                source_kind="website",
                                execution_mode="scheduled",
                                source_name=friendly_name,
                                website_url=url,
                                credential_ref=normalized_reference,
                                content_consent=content_consent,
                                ai=ai_config,
                                rag=rag_config,
                            ).model_dump(mode="json", exclude_none=True),
                        )
                    )
                finally:
                    schedule_repository.close()
            else:
                JobApplicationService(repository).enqueue_website_scan(
                    url=url,
                    credential_ref=normalized_reference,
                    content_consent=content_consent,
                    source_name=friendly_name,
                    idempotency_key=idempotency_key,
                    ai_config=ai_config,
                    rag_config=rag_config,
                )
        except (ValueError, JobStateError):
            MachineSecretStore(database_path.parent).delete(created_ai_reference)
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        notice = "schedule-saved" if execution_mode == "scheduled" else "scan-queued"
        return RedirectResponse(f"/jobs?notice={notice}", status_code=303)

    @app.get("/dashboard/jobs/status", include_in_schema=False)
    async def dashboard_job_status() -> JSONResponse:
        jobs_repository = SQLiteJobRepository(database_path)
        history_repository = SQLiteScanHistoryRepository(database_path)
        try:
            jobs = JobApplicationService(jobs_repository).list(limit=100)
            logs = [_job_log(job, history_repository) for job in jobs.items]
        finally:
            history_repository.close()
            jobs_repository.close()
        return JSONResponse(
            {
                "jobs": [
                    {
                        "id": job.id,
                        "display_id": job.display_id,
                        "status": job.status.value,
                        "progress": round(job.progress * 100),
                        "attempt_count": job.attempt_count,
                        "max_attempts": job.max_attempts,
                    }
                    for job in jobs.items
                ],
                "logs": logs,
            }
        )

    @app.post("/dashboard/worker/run-once", include_in_schema=False)
    async def dashboard_run_worker_once(
        request: Request,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        job = await run_in_threadpool(lambda: _run_one_dashboard_job(database_path))
        notice = "job-completed" if job is not None else "no-queued-job"
        return RedirectResponse(f"/?notice={notice}", status_code=303)

    @app.post("/dashboard/jobs/{job_id}/cancel", include_in_schema=False)
    async def dashboard_cancel_job(
        request: Request,
        job_id: str,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteJobRepository(database_path)
        try:
            JobApplicationService(repository).cancel(job_id)
        except JobNotFoundError:
            pass
        finally:
            repository.close()
        return RedirectResponse("/?notice=job-cancelled", status_code=303)

    @app.post("/dashboard/jobs/{job_id}/retry", include_in_schema=False)
    async def dashboard_retry_job(
        request: Request,
        job_id: str,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteJobRepository(database_path)
        try:
            JobApplicationService(repository).retry(job_id)
        except (JobNotFoundError, JobStateError):
            pass
        finally:
            repository.close()
        return RedirectResponse("/?notice=job-retried", status_code=303)

    @app.post("/dashboard/schedules/{schedule_id}/toggle", include_in_schema=False)
    async def dashboard_toggle_schedule(
        request: Request,
        schedule_id: str,
        csrf_token: Annotated[str, Form()],
        enabled: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteScheduleRepository(database_path)
        try:
            repository.set_enabled(schedule_id, enabled)
        finally:
            repository.close()
        return RedirectResponse("/jobs?notice=schedule-updated", status_code=303)

    @app.post("/dashboard/schedules/{schedule_id}/update", include_in_schema=False)
    async def dashboard_update_schedule(
        request: Request,
        schedule_id: str,
        csrf_token: Annotated[str, Form()],
        name: Annotated[str, Form(min_length=1, max_length=160)],
        interval_minutes: Annotated[int, Form(ge=15, le=525600)],
        next_run_at: Annotated[str, Form(min_length=10, max_length=80)],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        try:
            parsed = datetime.fromisoformat(next_run_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                parsed = parsed.astimezone()
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Invalid schedule date or time.") from error
        repository = SQLiteScheduleRepository(database_path)
        try:
            if not repository.update_schedule(
                schedule_id,
                name=name,
                interval_minutes=interval_minutes,
                next_run_at=parsed,
            ):
                raise HTTPException(status_code=404, detail="Schedule not found.")
        finally:
            repository.close()
        return RedirectResponse("/jobs?notice=schedule-updated", status_code=303)

    @app.post("/dashboard/schedules/{schedule_id}/delete", include_in_schema=False)
    async def dashboard_delete_schedule(
        request: Request,
        schedule_id: str,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteScheduleRepository(database_path)
        try:
            repository.delete(schedule_id)
        finally:
            repository.close()
        return RedirectResponse("/jobs?notice=schedule-deleted", status_code=303)


def _validate_csrf(request: Request, form_token: str) -> None:
    cookie_token = request.cookies.get("ragscanner_csrf", "")
    if not cookie_token or not hmac.compare_digest(cookie_token, form_token):
        raise HTTPException(status_code=403, detail="Dashboard form token is invalid.")


def _requires_local_administrator(request: Request) -> bool:
    path = request.url.path
    if path.startswith("/setup") or path == "/login" or path.startswith("/dashboard-assets/"):
        return False
    return (
        path == "/"
        or path.startswith("/sources")
        or path.startswith("/jobs")
        or path.startswith("/reports")
        or path.startswith("/compare")
        or path.startswith("/settings")
        or path.startswith("/dashboard/")
        or path.startswith("/api/v1/history")
    )


def _set_session_cookie(response: RedirectResponse, session: str) -> None:
    response.set_cookie(
        "ragscanner_session",
        session,
        httponly=True,
        samesite="strict",
        secure=False,
        max_age=8 * 60 * 60,
    )


def _set_csrf_cookie(response: HTMLResponse, token: str) -> None:
    response.set_cookie(
        "ragscanner_csrf",
        token,
        httponly=True,
        samesite="strict",
        secure=False,
        max_age=3600,
    )


def _date_filters(request: Request) -> tuple[datetime | None, datetime | None]:
    try:
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        lower = (
            datetime.combine(datetime.fromisoformat(date_from).date(), time.min, UTC)
            if date_from
            else None
        )
        upper = (
            datetime.combine(datetime.fromisoformat(date_to).date(), time.max, UTC)
            if date_to
            else None
        )
    except ValueError:
        return None, None
    return lower, upper


async def _openwebui_discovery_response() -> JSONResponse:
    services = await run_in_threadpool(
        lambda: discover_openwebui_services(include_container_runtimes=True)
    )
    return JSONResponse(
        {
            "environments": [
                {
                    "platform": "openwebui",
                    "base_url": item.base_url,
                    "status": "reachable",
                    "runtime": item.runtime or item.discovery_source,
                    "metadata_inventory_supported": True,
                    "capability_status": "connection_required",
                }
                for item in services
            ]
        }
    )


def _coverage(values: Mapping[str, object]) -> int:
    if not values:
        return 0
    assessed = 0
    for value in values.values():
        if isinstance(value, dict) and value.get("status") in {"assessed", "partial"}:
            assessed += 1
    return round(assessed / len(values) * 100)


def _job_log(job: JobRecord, history_repository: SQLiteScanHistoryRepository) -> dict[str, object]:
    """Build one bounded, secret-safe activity entry from durable state."""

    code = "job_queued"
    message = "The job is queued and waiting for the Host Service worker."
    level = "info"
    if job.status is JobStatus.RUNNING:
        code = "job_running"
        message = "The deterministic scan is running."
        if job.progress >= 0.96:
            code = "job_saving_report"
            message = "The report is being validated and saved."
        elif job.progress >= 0.8 and job.payload.get("ai", {}).get("enabled"):
            code = "ai_analysis_running"
            message = "The deterministic scan is complete and AI analysis is running."
    elif job.status is JobStatus.SUCCEEDED:
        code = "job_succeeded"
        message = "The scan completed and its report was saved."
        level = "success"
        ai_enabled = bool(job.payload.get("ai", {}).get("enabled"))
        if ai_enabled and job.result_ref and job.result_ref.startswith("history:"):
            report = history_repository.get(job.result_ref.removeprefix("history:"))
            if report is not None and report.ai_analysis_error_code:
                code = report.ai_analysis_error_code
                message = report.ai_analysis_error or "AI analysis was unavailable."
                level = "warning"
            elif report is not None and report.ai_analysis is not None:
                if report.ai_analysis.prompt_version == "2.3.0" and report.ai_analysis.limitations:
                    code = "ai_output_recovered"
                    message = (
                        "The model's structured output was invalid; a safe limited analysis "
                        "was saved."
                    )
                    level = "warning"
                else:
                    code = "ai_analysis_completed"
                    message = "The scan and AI-assisted report analysis completed successfully."
    elif job.status is JobStatus.FAILED:
        code = job.error_code or "job_failed"
        message = job.error_message or "The job failed."
        level = "error"
    elif job.status is JobStatus.CANCELLED:
        code = "job_cancelled"
        message = "The job was cancelled."
        level = "warning"
    elif job.status is JobStatus.CANCEL_REQUESTED:
        code = "job_cancellation_requested"
        message = "Cancellation was requested and will be applied at the next safe checkpoint."
        level = "warning"
    elif job.error_code:
        code = job.error_code
        message = job.error_message or "The previous attempt failed and will be retried."
        level = "warning"
    return {
        "job_id": job.id,
        "display_id": job.display_id,
        "timestamp": job.updated_at.isoformat(),
        "level": level,
        "code": code,
        "message": message,
    }


def _run_one_dashboard_job(database_path: Path) -> object | None:
    """Run one already-consented durable job from the localhost dashboard."""
    jobs_repository = SQLiteJobRepository(database_path)
    history_repository = SQLiteScanHistoryRepository(database_path)
    schedule_repository = SQLiteScheduleRepository(database_path)
    try:
        schedule_repository.materialize_due(jobs_repository)
        worker = DurableWorker(
            jobs_repository,
            {JobKind.SCAN: StaticScanJobHandler(StaticScanApplicationService(history_repository))},
            worker_id=f"dashboard:{os.getpid()}",
            lease_duration=timedelta(seconds=30),
        )
        return worker.run_once()
    finally:
        schedule_repository.close()
        history_repository.close()
        jobs_repository.close()
