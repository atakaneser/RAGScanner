from pathlib import Path

import httpx
import pytest
from ragscanner.api import API_VERSION, create_app
from ragscanner.api.auth import SlidingWindowRateLimiter
from ragscanner.storage import SQLiteScanHistoryRepository


def _test_bearer(suffix: str) -> str:
    return "synthetic-" + suffix + "-value"


def _seed(database: Path, report, finding) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    repository = SQLiteScanHistoryRepository(database)
    try:
        baseline = repository.save(report("scan-1", findings=[finding("a")]))
        candidate = repository.save(report("scan-2", findings=[finding("b")]))
    finally:
        repository.close()
    return baseline, candidate


@pytest.mark.anyio
async def test_local_api_exposes_health_history_detail_and_comparison(
    tmp_path: Path, report, finding
) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    baseline, candidate = _seed(database, report, finding)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)), base_url="http://testserver"
    ) as client:
        health = await client.get("/health")
        listed = await client.get("/api/v1/history", params={"limit": 1, "offset": 0})
        detail = await client.get(f"/api/v1/history/{baseline}")
        comparison = await client.get(f"/api/v1/history/{baseline}/compare/{candidate}")

    assert health.json() == {
        "status": "ok",
        "api_version": API_VERSION,
        "access_mode": "localhost_with_authenticated_job_control",
    }
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert len(listed.json()["items"]) == 1
    assert detail.status_code == 200
    assert detail.json()["scan"]["id"] == "scan-1"
    assert comparison.status_code == 200
    assert comparison.json()["compatible"] is True


@pytest.mark.anyio
async def test_local_api_uses_stable_bounded_errors_without_existence_details(
    tmp_path: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://testserver",
    ) as client:
        missing = await client.get(f"/api/v1/history/{'a' * 32}")
        invalid = await client.get("/api/v1/history/not-an-id")
        oversized = await client.get("/health", headers={"content-length": "1000001"})
        invalid_length = await client.get("/health", headers={"content-length": "unknown"})
        untrusted = await client.get("/health", headers={"host": "attacker.example"})

    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "history_not_found",
            "message": "Scan history record was not found.",
        }
    }
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "request_too_large"
    assert invalid_length.status_code == 400
    assert invalid_length.json()["error"]["code"] == "invalid_content_length"
    assert untrusted.status_code == 400
    assert untrusted.json()["error"]["code"] == "invalid_host"


@pytest.mark.anyio
async def test_local_api_openapi_is_versioned_with_authenticated_job_control(
    tmp_path: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://testserver",
    ) as client:
        schema = (await client.get("/openapi.json")).json()

    assert schema["info"]["version"] == API_VERSION
    assert schema["paths"]["/api/v1/scans"]["post"]["security"]
    assert schema["paths"]["/api/v1/jobs"]["get"]["security"]
    assert set(schema["paths"]["/api/v1/history"]) == {"get"}


@pytest.mark.anyio
async def test_authenticated_scan_creation_is_scoped_rate_limited_and_idempotent(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.txt"
    source.write_text("Synthetic knowledge content.", encoding="utf-8")
    other_source = tmp_path / "other.txt"
    other_source.write_text("Different synthetic content.", encoding="utf-8")
    token = _test_bearer("writer")
    app = create_app(
        database,
        api_keys={"writer": (token, {"scans:write", "jobs:read", "jobs:cancel"})},
    )
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "scan:synthetic:001"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        missing = await client.post(
            "/api/v1/scans",
            json={"path": str(source)},
            headers={"Idempotency-Key": "scan:missing:001"},
        )
        first = await client.post("/api/v1/scans", json={"path": str(source)}, headers=headers)
        second = await client.post("/api/v1/scans", json={"path": str(source)}, headers=headers)
        conflict = await client.post(
            "/api/v1/scans", json={"path": str(other_source)}, headers=headers
        )
        listed = await client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token}"})
        forbidden = await client.post(
            f"/api/v1/jobs/{first.json()['job']['id']}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert first.status_code == 202
    assert first.json()["job"]["id"] == second.json()["job"]["id"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "invalid_job_state"
    assert listed.json()["total"] == 1
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "insufficient_scope"


@pytest.mark.anyio
async def test_authenticated_job_routes_enforce_rate_limit(tmp_path: Path) -> None:
    token = _test_bearer("reader")
    limiter = SlidingWindowRateLimiter(maximum_requests=1, window_seconds=60)
    app = create_app(
        tmp_path / "history.sqlite3",
        api_keys={"reader": (token, {"jobs:read"})},
        rate_limiter=limiter,
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        first = await client.get("/api/v1/jobs", headers=headers)
        second = await client.get("/api/v1/jobs", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"


@pytest.mark.anyio
async def test_local_api_corrupt_database_returns_generic_unavailable_error(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    database.write_bytes(b"hostile-database-content")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/history")

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "history_unavailable", "message": "Local scan history is unavailable."}
    }
    assert "hostile-database-content" not in response.text
