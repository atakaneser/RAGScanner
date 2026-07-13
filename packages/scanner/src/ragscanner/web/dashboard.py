"""Jinja dashboard routes composed over application services."""

import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ragscanner.application import HistoryApplicationService, JobApplicationService
from ragscanner.jobs import JobNotFoundError, JobStateError
from ragscanner.storage import SQLiteJobRepository, SQLiteScanHistoryRepository

DASHBOARD_ASSET_ROOT = Path(__file__).with_name("templates")
templates = Jinja2Templates(directory=DASHBOARD_ASSET_ROOT)


def _display_timestamp(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone().strftime("%Y-%m-%d %H:%M %Z")


templates.env.filters["display_timestamp"] = _display_timestamp


def register_dashboard(app: FastAPI, database_path: Path) -> None:
    """Register localhost-only HTML routes without exposing API credentials to the browser."""

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request) -> HTMLResponse:
        jobs_repository = SQLiteJobRepository(database_path)
        history_repository = SQLiteScanHistoryRepository(database_path)
        try:
            jobs = JobApplicationService(jobs_repository).list(limit=8)
            history_service = HistoryApplicationService(history_repository)
            history = history_service.list(limit=8)
            latest_report = (
                history_service.get(history.items[0].history_id) if history.items else None
            )
        finally:
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
                "scans": history.items,
                "scan_total": history.total,
                "latest": history.items[0] if history.items else None,
                "coverage": coverage,
                "csrf_token": csrf_token,
                "request_id": secrets.token_hex(16),
            },
        )
        response.set_cookie(
            "ragscanner_csrf",
            csrf_token,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=3600,
        )
        return response

    @app.post("/dashboard/scans/local", include_in_schema=False)
    async def dashboard_local_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        path: Annotated[str, Form(min_length=1, max_length=4096)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        scan_consent: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        _validate_csrf(request, csrf_token)
        if not scan_consent:
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        repository = SQLiteJobRepository(database_path)
        try:
            JobApplicationService(repository).enqueue_local_scan(
                Path(path), idempotency_key=idempotency_key
            )
        except (OSError, ValueError, JobStateError):
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/?notice=scan-queued", status_code=303)

    @app.post("/dashboard/scans/openwebui", include_in_schema=False)
    async def dashboard_openwebui_scan(
        request: Request,
        csrf_token: Annotated[str, Form()],
        base_url: Annotated[str, Form(min_length=1, max_length=2048)],
        knowledge_id: Annotated[str, Form(min_length=1, max_length=240)],
        credential_ref: Annotated[str, Form(min_length=1, max_length=500)],
        idempotency_key: Annotated[str, Form(min_length=8, max_length=160)],
        content_consent: Annotated[bool, Form()] = False,
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
            )
        except (ValueError, JobStateError):
            return RedirectResponse("/?notice=invalid-scan", status_code=303)
        finally:
            repository.close()
        return RedirectResponse("/?notice=scan-queued", status_code=303)

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


def _coverage(values: Mapping[str, object]) -> int:
    if not values:
        return 0
    assessed = 0
    for value in values.values():
        if isinstance(value, dict) and value.get("status") in {"assessed", "partial"}:
            assessed += 1
    return round(assessed / len(values) * 100)
