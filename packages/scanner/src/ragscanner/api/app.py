"""Versioned local API with read history and authenticated asynchronous job control."""

import os
import re
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from ragscanner.api.auth import (
    ApiAuthenticationError,
    ApiAuthorizationError,
    ApiKeyStore,
    ApiPrincipal,
    ApiRateLimitError,
    SlidingWindowRateLimiter,
)
from ragscanner.api.models import (
    ApiHealth,
    JobAccepted,
    LocalScanCreateRequest,
    OpenWebUIScanCreateRequest,
)
from ragscanner.application import (
    HistoryApplicationService,
    HistoryNotFoundError,
    JobApplicationService,
)
from ragscanner.config import get_settings
from ragscanner.history import ScanComparison, ScanHistoryPage
from ragscanner.jobs import JobNotFoundError, JobPage, JobRecord, JobStateError
from ragscanner.reporting.models import ReportDocument
from ragscanner.storage import SQLiteJobRepository, SQLiteScanHistoryRepository
from ragscanner.storage.database import StorageError
from ragscanner.web import register_dashboard
from ragscanner.web.dashboard import DASHBOARD_ASSET_ROOT

API_VERSION = "1.0.0-alpha"
MAX_REQUEST_BYTES = 1_000_000
_HISTORY_ID_PATTERN = r"^[a-f0-9]{32}$"
_JOB_ID_PATTERN = r"^[a-f0-9]{32}$"
_LOCAL_HOST = re.compile(r"^(?:127\.0\.0\.1|localhost|testserver|\[::1\])(?::\d{1,5})?$")
ALL_API_SCOPES = {"scans:write", "jobs:read", "jobs:cancel", "jobs:retry"}


def create_app(
    database_path: Path | None = None,
    *,
    api_keys: Mapping[str, tuple[str, set[str]]] | None = None,
    rate_limiter: SlidingWindowRateLimiter | None = None,
) -> FastAPI:
    """Create the local API with explicit storage and in-memory authentication composition."""
    selected_database = (database_path or (get_settings().data_dir / "history.sqlite3")).resolve()
    configured_keys = dict(api_keys or {})
    environment_key = os.environ.get("RAGSCANNER_API_KEY")
    if not configured_keys and environment_key:
        configured_keys["local-environment"] = (environment_key, ALL_API_SCOPES)
    key_store = ApiKeyStore(configured_keys)
    limiter = rate_limiter or SlidingWindowRateLimiter()
    bearer_scheme = HTTPBearer(auto_error=False)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(
        title="RAGScanner Local API",
        summary="Local scan history and authenticated asynchronous scan API.",
        description=(
            "Technical alpha API. Read routes remain loopback-local. Scan and job-control routes "
            "require a scoped Bearer API key and enqueue durable work."
        ),
        version=API_VERSION,
        lifespan=lifespan,
    )
    app.mount(
        "/dashboard-assets",
        StaticFiles(directory=DASHBOARD_ASSET_ROOT),
        name="dashboard-assets",
    )

    @app.middleware("http")
    async def security_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        if not _LOCAL_HOST.fullmatch(request.headers.get("host", "")):
            return _error(400, "invalid_host", "Host header is not allowed by the local API.")
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                parsed_length = int(content_length)
                if parsed_length < 0:
                    raise ValueError
                if parsed_length > MAX_REQUEST_BYTES:
                    return _error(413, "request_too_large", "Request body exceeds the API limit.")
            except ValueError:
                return _error(400, "invalid_content_length", "Content-Length must be an integer.")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(HistoryNotFoundError)
    async def history_not_found(
        _request: Request, _error_value: HistoryNotFoundError
    ) -> JSONResponse:
        return _error(404, "history_not_found", "Scan history record was not found.")

    @app.exception_handler(StorageError)
    async def storage_unavailable(_request: Request, _error_value: StorageError) -> JSONResponse:
        return _error(503, "history_unavailable", "Local scan history is unavailable.")

    @app.exception_handler(ApiAuthenticationError)
    async def authentication_required(
        _request: Request, _error_value: ApiAuthenticationError
    ) -> JSONResponse:
        response = _error(401, "authentication_required", "A valid Bearer API key is required.")
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(ApiAuthorizationError)
    async def scope_required(
        _request: Request, _error_value: ApiAuthorizationError
    ) -> JSONResponse:
        return _error(403, "insufficient_scope", "The API key does not grant this operation.")

    @app.exception_handler(ApiRateLimitError)
    async def rate_limited(_request: Request, _error_value: ApiRateLimitError) -> JSONResponse:
        response = _error(429, "rate_limited", "The API key request rate was exceeded.")
        response.headers["Retry-After"] = "60"
        return response

    @app.exception_handler(JobNotFoundError)
    async def job_not_found(_request: Request, _error_value: JobNotFoundError) -> JSONResponse:
        return _error(404, "job_not_found", "Job was not found.")

    @app.exception_handler(JobStateError)
    async def invalid_job_state(_request: Request, _error_value: JobStateError) -> JSONResponse:
        return _error(409, "invalid_job_state", "The job cannot perform this transition.")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        _request: Request, _error_value: RequestValidationError
    ) -> JSONResponse:
        return _error(422, "invalid_request", "Request parameters are invalid.")

    def history_service() -> Iterator[HistoryApplicationService]:
        repository = SQLiteScanHistoryRepository(selected_database)
        try:
            yield HistoryApplicationService(repository)
        finally:
            repository.close()

    def job_service() -> Iterator[JobApplicationService]:
        repository = SQLiteJobRepository(selected_database)
        try:
            yield JobApplicationService(repository)
        finally:
            repository.close()

    def require_scope(scope: str):  # type: ignore[no-untyped-def]
        def dependency(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        ) -> ApiPrincipal:
            if credentials is None or credentials.scheme.casefold() != "bearer":
                raise ApiAuthenticationError
            principal = key_store.authenticate(credentials.credentials)
            if scope not in principal.scopes:
                raise ApiAuthorizationError
            limiter.check(principal.key_id)
            return principal

        return dependency

    Service = Annotated[HistoryApplicationService, Depends(history_service)]
    JobService = Annotated[JobApplicationService, Depends(job_service)]

    @app.get("/health", response_model=ApiHealth, tags=["system"])
    async def health() -> ApiHealth:
        return ApiHealth(
            api_version=API_VERSION,
            access_mode="localhost_with_authenticated_job_control",
        )

    @app.get("/api/v1/history", response_model=ScanHistoryPage, tags=["history"])
    async def list_history(
        service: Service,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ScanHistoryPage:
        return service.list(limit=limit, offset=offset)

    @app.get("/api/v1/history/{history_id}", response_model=ReportDocument, tags=["history"])
    async def history_detail(
        service: Service,
        history_id: Annotated[
            str, ApiPath(min_length=32, max_length=32, pattern=_HISTORY_ID_PATTERN)
        ],
    ) -> ReportDocument:
        return service.get(history_id)

    @app.get(
        "/api/v1/history/{baseline_history_id}/compare/{candidate_history_id}",
        response_model=ScanComparison,
        tags=["history"],
    )
    async def compare_history(
        service: Service,
        baseline_history_id: Annotated[
            str, ApiPath(min_length=32, max_length=32, pattern=_HISTORY_ID_PATTERN)
        ],
        candidate_history_id: Annotated[
            str, ApiPath(min_length=32, max_length=32, pattern=_HISTORY_ID_PATTERN)
        ],
    ) -> ScanComparison:
        return service.compare(baseline_history_id, candidate_history_id)

    @app.post("/api/v1/scans", response_model=JobAccepted, status_code=202, tags=["scans"])
    async def create_local_scan(
        request: LocalScanCreateRequest,
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("scans:write"))],
        idempotency_key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=8, max_length=160)
        ],
    ) -> JobAccepted:
        try:
            job = service.enqueue_local_scan(
                Path(request.path),
                config_path=Path(request.config_path) if request.config_path else None,
                idempotency_key=idempotency_key,
                max_attempts=request.max_attempts,
            )
        except (OSError, ValueError) as error:
            raise RequestValidationError([]) from error
        return JobAccepted(job=job)

    @app.post(
        "/api/v1/scans/openwebui",
        response_model=JobAccepted,
        status_code=202,
        tags=["scans"],
    )
    async def create_openwebui_scan(
        request: OpenWebUIScanCreateRequest,
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("scans:write"))],
        idempotency_key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=8, max_length=160)
        ],
    ) -> JobAccepted:
        try:
            job = service.enqueue_openwebui_scan(
                base_url=request.base_url,
                knowledge_id=request.knowledge_id,
                credential_ref=request.credential_ref,
                content_consent=request.content_consent,
                idempotency_key=idempotency_key,
                max_attempts=request.max_attempts,
            )
        except ValueError as error:
            raise RequestValidationError([]) from error
        return JobAccepted(job=job)

    @app.get("/api/v1/jobs", response_model=JobPage, tags=["jobs"])
    async def list_jobs(
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("jobs:read"))],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> JobPage:
        return service.list(limit=limit, offset=offset)

    @app.get("/api/v1/jobs/{job_id}", response_model=JobRecord, tags=["jobs"])
    async def job_detail(
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("jobs:read"))],
        job_id: Annotated[str, ApiPath(min_length=32, max_length=32, pattern=_JOB_ID_PATTERN)],
    ) -> JobRecord:
        return service.get(job_id)

    @app.post("/api/v1/jobs/{job_id}/cancel", response_model=JobRecord, tags=["jobs"])
    async def cancel_job(
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("jobs:cancel"))],
        job_id: Annotated[str, ApiPath(min_length=32, max_length=32, pattern=_JOB_ID_PATTERN)],
    ) -> JobRecord:
        return service.cancel(job_id)

    @app.post("/api/v1/jobs/{job_id}/retry", response_model=JobRecord, tags=["jobs"])
    async def retry_job(
        service: JobService,
        _principal: Annotated[ApiPrincipal, Depends(require_scope("jobs:retry"))],
        job_id: Annotated[str, ApiPath(min_length=32, max_length=32, pattern=_JOB_ID_PATTERN)],
    ) -> JobRecord:
        return service.retry(job_id)

    register_dashboard(app, selected_database)

    return app


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
