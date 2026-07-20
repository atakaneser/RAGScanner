"""Jinja dashboard routes composed over application services."""

import hashlib
import hmac
import os
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.application import (
    DurableWorker,
    HistoryApplicationService,
    JobApplicationService,
    StaticScanApplicationService,
    StaticScanJobHandler,
    resolve_secret_reference,
)
from ragscanner.jobs import JobKind, JobNotFoundError, JobRecord, JobStateError, JobStatus
from ragscanner.local_auth import LocalAdministratorStore
from ragscanner.onboarding import (
    OpenWebUIDiscoveryError,
    discover_local_rag_environments,
    discover_openwebui_knowledge_bases,
)
from ragscanner.providers import PROVIDER_CATALOG, ModelProviderError, discover_provider_models
from ragscanner.storage import (
    ENV_CREDENTIAL_REFERENCE_ERROR,
    SourceProfile,
    SQLiteJobRepository,
    SQLiteScanHistoryRepository,
    SQLiteSourceProfileRepository,
    normalize_env_credential_reference,
)

DASHBOARD_ASSET_ROOT = Path(__file__).with_name("templates")
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


def _source_secret_reference(profile_id: str) -> str:
    return f"env:RAGSCANNER_SOURCE_{profile_id.upper()}_API_KEY"


def _ai_secret_reference() -> str:
    return f"env:RAGSCANNER_AI_{secrets.token_hex(12).upper()}_API_KEY"


def _remember_process_secret(reference: str, value: str) -> None:
    """Keep a dashboard-supplied secret in Host memory, never in SQLite or a job payload."""

    secret = value.strip()
    if not secret:
        raise ValueError("API key cannot be empty")
    os.environ[reference.removeprefix("env:")] = secret


def _effective_source_profile(profile: SourceProfile) -> SourceProfile:
    if profile.kind == "filesystem":
        status = "scan_ready"
    elif profile.kind != "openwebui":
        status = "metadata_only"
    else:
        try:
            if not profile.credential_ref:
                raise ValueError("missing credential")
            resolve_secret_reference(profile.credential_ref)
        except ValueError:
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
) -> AIProviderConfig:
    secret = api_key.strip() if api_key else ""
    reference = normalize_env_credential_reference(credential_ref) if credential_ref else None
    if secret:
        reference = _ai_secret_reference()
    config = AIProviderConfig(
        enabled=enabled,
        provider=provider.strip() if provider else None,
        model=model.strip() if model else None,
        base_url=base_url.strip() if base_url else None,
        credential_ref=reference,
        remote_consent=remote_consent,
    )
    if secret and reference:
        _remember_process_secret(reference, secret)
    return config


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
        return await _environment_inventory_response()

    @app.post("/setup", response_class=HTMLResponse, response_model=None, include_in_schema=False)
    async def create_local_administrator(
        request: Request,
        username: Annotated[str, Form(min_length=3, max_length=80)],
        password: Annotated[str, Form(min_length=14, max_length=512)],
        csrf_token: Annotated[str, Form()],
        interface_mode: Annotated[str, Form(pattern=r"^(web|cli)$")] = "web",
        source_mode: Annotated[
            str, Form(pattern=r"^(openwebui|environment|temporary_folder)$")
        ] = "openwebui",
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
                kind = "openwebui" if source_mode == "openwebui" else "generic"
                pending_profile = SourceProfile(
                    name=(source_name or kind).strip(),
                    kind=kind,
                    base_url=source_location.strip(),
                    credential_ref=None,
                    discovery_origin="setup",
                    capability_status="connection_required"
                    if kind == "openwebui"
                    else "metadata_only",
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
                    sources.save(pending_profile)
                    if api_key and pending_profile.credential_ref:
                        _remember_process_secret(pending_profile.credential_ref, api_key)
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
        try:
            jobs = JobApplicationService(jobs_repository).list(limit=100)
            history_service = HistoryApplicationService(history_repository)
            date_from, date_to = _date_filters(request)
            selected_source = request.query_params.get("source") or None
            history = history_service.list(
                limit=100,
                created_after=date_from,
                created_before=date_to,
                source=selected_source,
            )
            all_history = history_service.list(limit=200)
            latest_report = (
                history_service.get(all_history.items[0].history_id) if all_history.items else None
            )
            selected_report = history_service.get(report_id) if report_id else None
            comparison = (
                history_service.compare(baseline_id, candidate_id)
                if baseline_id and candidate_id
                else None
            )
            profiles = [_effective_source_profile(profile) for profile in source_repository.list()]
            job_logs = [_job_log(job, history_repository) for job in jobs.items]
        finally:
            source_repository.close()
            history_repository.close()
            jobs_repository.close()
        csrf_token = request.cookies.get("ragscanner_csrf") or secrets.token_urlsafe(32)
        coverage = _coverage(latest_report.assessment_coverage if latest_report else {})
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
                "page": page,
                "profiles": profiles,
                "selected_report": selected_report,
                "selected_report_id": report_id,
                "comparison": comparison,
                "baseline_id": baseline_id,
                "candidate_id": candidate_id,
                "csrf_token": csrf_token,
                "request_id": secrets.token_hex(16),
                "notice": request.query_params.get("notice", ""),
                "host_auth_enabled": administrator_store is not None,
                "ai_providers": PROVIDER_CATALOG,
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

    @app.post("/dashboard/sources", include_in_schema=False)
    async def dashboard_add_source(
        request: Request,
        csrf_token: Annotated[str, Form()],
        name: Annotated[str, Form(min_length=1, max_length=160)],
        kind: Annotated[
            str,
            Form(
                pattern=(
                    r"^(openwebui|filesystem|qdrant|chroma|weaviate|milvus|pgvector|"
                    r"elasticsearch|opensearch|pinecone|kubernetes|generic|custom)$"
                )
            ),
        ],
        location: Annotated[str, Form(min_length=1, max_length=4096)],
        credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        api_key: Annotated[str | None, Form(max_length=4096)] = None,
        discovery_origin: Annotated[str, Form(max_length=80)] = "manual",
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteSourceProfileRepository(database_path)
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
                    if kind == "filesystem"
                    else "connection_required"
                    if kind == "openwebui"
                    else "metadata_only"
                ),
            )
            normalized_reference = normalize_env_credential_reference(credential_ref)
            if api_key:
                normalized_reference = _source_secret_reference(profile.id)
            profile = profile.model_copy(
                update={
                    "credential_ref": normalized_reference,
                    "capability_status": (
                        "scan_ready"
                        if kind == "openwebui" and (api_key or normalized_reference)
                        else profile.capability_status
                    ),
                }
            )
            repository.save(profile)
            if api_key and profile.credential_ref:
                _remember_process_secret(profile.credential_ref, api_key)
        except ValueError:
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
            reference = normalize_env_credential_reference(credential_ref)
            if api_key:
                reference = _source_secret_reference(profile.id)
                _remember_process_secret(reference, api_key)
            if not reference:
                return JSONResponse({"error": "Enter an API key to continue."}, status_code=400)
            resolved = resolve_secret_reference(reference)
            knowledge_bases = await run_in_threadpool(
                lambda: discover_openwebui_knowledge_bases(profile.base_url or "", resolved)
            )
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
            repository.delete(profile_id)
        finally:
            repository.close()
        return RedirectResponse("/sources?notice=source-deleted", status_code=303)

    @app.post("/dashboard/scans/local", include_in_schema=False)
    async def dashboard_local_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        path: Annotated[str, Form(min_length=1, max_length=4096)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        scan_consent: Annotated[bool, Form()] = False,
        ai_enabled: Annotated[bool, Form()] = False,
        ai_provider: Annotated[str | None, Form(max_length=80)] = None,
        ai_model: Annotated[str | None, Form(max_length=240)] = None,
        ai_base_url: Annotated[str | None, Form(max_length=2048)] = None,
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        ai_remote_consent: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        if not scan_consent:
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        repository = SQLiteJobRepository(database_path)
        try:
            JobApplicationService(repository).enqueue_local_scan(
                Path(path),
                idempotency_key=idempotency_key,
                ai_config=_ai_config(
                    ai_enabled,
                    ai_provider,
                    ai_model,
                    ai_base_url,
                    ai_credential_ref,
                    ai_remote_consent,
                    ai_api_key,
                ),
            )
        except (OSError, ValueError, JobStateError):
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/?notice=scan-queued", status_code=303)

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
        return await _environment_inventory_response()

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
        try:
            config = _ai_config(
                True,
                provider,
                "model-inventory",
                base_url,
                credential_ref,
                remote_consent,
                api_key,
            )
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
        return JSONResponse({"models": models})

    @app.post("/dashboard/scans/openwebui", include_in_schema=False)
    async def dashboard_openwebui_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        base_url: Annotated[str, Form(min_length=1, max_length=2048)],
        knowledge_id: Annotated[str, Form(min_length=1, max_length=240)],
        credential_ref: Annotated[str, Form(min_length=1, max_length=500)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        content_consent: Annotated[bool, Form()] = False,
        ai_enabled: Annotated[bool, Form()] = False,
        ai_provider: Annotated[str | None, Form(max_length=80)] = None,
        ai_model: Annotated[str | None, Form(max_length=240)] = None,
        ai_base_url: Annotated[str | None, Form(max_length=2048)] = None,
        ai_credential_ref: Annotated[str | None, Form(max_length=500)] = None,
        ai_api_key: Annotated[str | None, Form(max_length=4096)] = None,
        ai_remote_consent: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        repository = SQLiteJobRepository(database_path)
        try:
            JobApplicationService(repository).enqueue_openwebui_scan(
                base_url=base_url,
                knowledge_id=knowledge_id,
                credential_ref=credential_ref,
                content_consent=content_consent,
                idempotency_key=idempotency_key,
                ai_config=_ai_config(
                    ai_enabled,
                    ai_provider,
                    ai_model,
                    ai_base_url,
                    ai_credential_ref,
                    ai_remote_consent,
                    ai_api_key,
                ),
            )
        except (ValueError, JobStateError):
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/?notice=scan-queued", status_code=303)

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


async def _environment_inventory_response() -> JSONResponse:
    environments = await run_in_threadpool(
        lambda: discover_local_rag_environments(
            include_container_runtimes=True, include_kubernetes=True
        )
    )
    return JSONResponse(
        {
            "environments": [
                {
                    "platform": item.platform,
                    "base_url": item.base_url,
                    "status": item.discovery_status,
                    "runtime": item.runtime,
                    "metadata_inventory_supported": item.metadata_inventory_supported,
                    "capability_status": (
                        "scan_ready"
                        if item.platform == "openwebui" and item.discovery_status == "reachable"
                        else "metadata_only"
                        if item.discovery_status in {"reachable", "detected"}
                        else "connection_required"
                    ),
                }
                for item in environments
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
        "timestamp": job.updated_at.isoformat(),
        "level": level,
        "code": code,
        "message": message,
    }


def _run_one_dashboard_job(database_path: Path) -> object | None:
    """Run one already-consented durable job from the localhost dashboard."""
    jobs_repository = SQLiteJobRepository(database_path)
    history_repository = SQLiteScanHistoryRepository(database_path)
    try:
        worker = DurableWorker(
            jobs_repository,
            {JobKind.SCAN: StaticScanJobHandler(StaticScanApplicationService(history_repository))},
            worker_id=f"dashboard:{os.getpid()}",
            lease_duration=timedelta(seconds=30),
        )
        return worker.run_once()
    finally:
        history_repository.close()
        jobs_repository.close()
