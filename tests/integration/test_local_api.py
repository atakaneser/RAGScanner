import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from ragscanner.api import API_VERSION, create_app
from ragscanner.api.auth import SlidingWindowRateLimiter
from ragscanner.application import resolve_secret_reference
from ragscanner.storage import SQLiteScanHistoryRepository, SQLiteSourceProfileRepository
from ragscanner.storage.schema import scans
from sqlalchemy import update


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
async def test_history_api_filters_and_paginates_a_large_result_set(tmp_path: Path, report) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    repository = SQLiteScanHistoryRepository(database)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    try:
        for index in range(240):
            source = "Selected source" if index % 3 == 0 else "Other source"
            history_id = repository.save(
                report(f"scale-{index}", source_name=source, overall=index % 101)
            )
            with repository.engine.begin() as connection:
                connection.execute(
                    update(scans)
                    .where(scans.c.id == history_id)
                    .values(created_at=(base + timedelta(minutes=index)).isoformat())
                )
    finally:
        repository.close()

    lower = base + timedelta(minutes=60)
    upper = base + timedelta(minutes=179)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/history",
            params={
                "limit": 25,
                "offset": 5,
                "created_after": lower.isoformat(),
                "created_before": upper.isoformat(),
                "source": "Selected source",
            },
        )
        reversed_range = await client.get(
            "/api/v1/history",
            params={"created_after": upper.isoformat(), "created_before": lower.isoformat()},
        )
        naive_range = await client.get(
            "/api/v1/history", params={"created_after": "2026-01-01T00:00:00"}
        )
        oversized_page = await client.get("/api/v1/history", params={"limit": 201})

    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == 40
    assert payload["limit"] == 25
    assert payload["offset"] == 5
    assert len(payload["items"]) == 25
    assert {item["source_name"] for item in payload["items"]} == {"Selected source"}
    assert payload["items"] == sorted(
        payload["items"], key=lambda item: (item["created_at"], item["history_id"]), reverse=True
    )
    assert reversed_range.status_code == 422
    assert naive_range.status_code == 422
    assert oversized_page.status_code == 422


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
async def test_local_api_accepts_the_fixed_localhost_dashboard_hostname(
    tmp_path: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://localhost:8765",
    ) as client:
        response = await client.get("/health")
        wrong_port = await client.get("/health", headers={"host": "localhost:8123"})

    assert response.status_code == 200
    assert wrong_port.status_code == 400
    assert wrong_port.json()["error"]["code"] == "invalid_host"


@pytest.mark.anyio
async def test_local_api_rejects_the_retired_custom_dashboard_hostname(
    tmp_path: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://local.ragscanner.com",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_host"


@pytest.mark.anyio
async def test_host_dashboard_bootstraps_and_requires_a_local_administrator(tmp_path: Path) -> None:
    app = create_app(
        tmp_path / "history.sqlite3", local_administrator_data_dir=tmp_path / "host-data"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8765",
        follow_redirects=False,
    ) as client:
        initial = await client.get("/")
        setup = await client.get("/setup")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert csrf is not None
        protected_history = await client.get("/api/v1/history")
        created = await client.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": csrf.group(1),
            },
        )
        dashboard = await client.get("/")

    assert initial.status_code == 303
    assert initial.headers["location"] == "/setup"
    assert setup.status_code == 200
    assert "Set up this machine" in setup.text
    assert 'name="api_key"' in setup.text
    assert "never stored in SQLite, reports, or scan jobs" in setup.text
    assert "/dashboard-assets/dashboard-i18n.js?v=" in setup.text
    assert 'data-language-picker aria-label="Language"' in setup.text
    assert protected_history.status_code == 401
    assert protected_history.json()["error"]["code"] == "setup_required"
    assert created.status_code == 303
    assert dashboard.status_code == 200
    assert "Overview" in dashboard.text


@pytest.mark.anyio
async def test_host_dashboard_changes_password_and_invalidates_other_sessions(
    tmp_path: Path,
) -> None:
    app = create_app(
        tmp_path / "history.sqlite3", local_administrator_data_dir=tmp_path / "host-data"
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8765",
            follow_redirects=False,
        ) as primary,
        httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8765",
            follow_redirects=False,
        ) as secondary,
    ):
        setup = await primary.get("/setup")
        setup_csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert setup_csrf is not None
        created = await primary.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": setup_csrf.group(1),
            },
        )
        signed_in = await secondary.post(
            "/login",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
            },
        )
        settings = await primary.get("/settings")
        settings_csrf = re.search(r'name="csrf_token" value="([^"]+)"', settings.text)
        assert settings_csrf is not None
        invalid_current = await primary.post(
            "/dashboard/password",
            data={
                "csrf_token": settings_csrf.group(1),
                "current_password": "incorrect password",
                "new_password": "a different long local password",
                "confirm_password": "a different long local password",
            },
        )
        weak_password = await primary.post(
            "/dashboard/password",
            data={
                "csrf_token": settings_csrf.group(1),
                "current_password": "a long local-only password",
                "new_password": "too short",
                "confirm_password": "too short",
            },
        )
        mismatch = await primary.post(
            "/dashboard/password",
            data={
                "csrf_token": settings_csrf.group(1),
                "current_password": "a long local-only password",
                "new_password": "a different long local password",
                "confirm_password": "another different local password",
            },
        )
        changed = await primary.post(
            "/dashboard/password",
            data={
                "csrf_token": settings_csrf.group(1),
                "current_password": "a long local-only password",
                "new_password": "a different long local password",
                "confirm_password": "a different long local password",
            },
        )
        primary_after = await primary.get("/settings")
        secondary_after = await secondary.get("/")
        old_login = await secondary.post(
            "/login",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
            },
        )
        new_login = await secondary.post(
            "/login",
            data={
                "username": "host-admin",
                "password": "a different long local password",
            },
        )

    assert created.status_code == 303
    assert signed_in.status_code == 303
    assert "Change administrator password" in settings.text
    assert invalid_current.headers["location"] == "/settings?notice=password-current-invalid"
    assert weak_password.headers["location"] == "/settings?notice=password-invalid"
    assert mismatch.headers["location"] == "/settings?notice=password-mismatch"
    assert changed.status_code == 303
    assert changed.headers["location"] == "/settings?notice=password-changed"
    assert primary_after.status_code == 200
    assert secondary_after.status_code == 303
    assert secondary_after.headers["location"] == "/login"
    assert old_login.status_code == 401
    assert new_login.status_code == 303


@pytest.mark.anyio
async def test_host_setup_persists_interface_and_first_source_profile(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    app = create_app(database, local_administrator_data_dir=tmp_path / "host-data")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8765",
        follow_redirects=False,
    ) as client:
        setup = await client.get("/setup")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert csrf is not None
        response = await client.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": csrf.group(1),
                "interface_mode": "web",
                "source_mode": "openwebui",
                "source_name": "Product knowledge",
                "source_location": "http://127.0.0.1:3000",
                "credential_ref": "env:OPENWEBUI_API_KEY",
            },
        )

    repository = SQLiteSourceProfileRepository(database)
    try:
        profiles = repository.list()
        assert repository.setting("interface_mode") == "web"
        assert repository.setting("initial_source_mode") == "openwebui"
    finally:
        repository.close()
    assert response.status_code == 303
    assert len(profiles) == 1
    assert profiles[0].name == "Product knowledge"
    assert profiles[0].credential_ref == "env:OPENWEBUI_API_KEY"


@pytest.mark.anyio
async def test_host_setup_rejects_raw_api_key_without_echoing_or_persisting_it(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    submitted_value = "synthetic-raw-credential-value"
    app = create_app(database, local_administrator_data_dir=tmp_path / "host-data")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8765",
        follow_redirects=False,
    ) as client:
        setup = await client.get("/setup")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert csrf is not None
        response = await client.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": csrf.group(1),
                "interface_mode": "web",
                "source_mode": "openwebui",
                "source_name": "Product knowledge",
                "source_location": "http://127.0.0.1:3000",
                "credential_ref": submitted_value,
            },
        )

    assert response.status_code == 400
    assert "not the API key itself" in response.text
    assert submitted_value not in response.text
    assert f'name="csrf_token" value="{csrf.group(1)}"' in response.text
    assert not database.exists() or submitted_value.encode() not in database.read_bytes()


@pytest.mark.anyio
async def test_host_setup_persists_api_key_outside_sqlite(
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    submitted_value = "synthetic-setup-api-key"
    app = create_app(database, local_administrator_data_dir=tmp_path / "host-data")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8765",
        follow_redirects=False,
    ) as client:
        setup = await client.get("/setup")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert csrf is not None
        response = await client.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": csrf.group(1),
                "source_mode": "openwebui",
                "source_name": "Product knowledge",
                "source_location": "http://127.0.0.1:3000",
                "api_key": submitted_value,
            },
        )

    repository = SQLiteSourceProfileRepository(database)
    try:
        profile = repository.list()[0]
    finally:
        repository.close()

    assert response.status_code == 303
    assert profile.credential_ref is not None
    assert profile.credential_ref.startswith("file-secret:")
    assert submitted_value.encode() not in database.read_bytes()
    assert resolve_secret_reference(profile.credential_ref) == submitted_value


@pytest.mark.anyio
async def test_host_setup_allows_openwebui_connection_to_be_completed_later(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    app = create_app(database, local_administrator_data_dir=tmp_path / "host-data")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8765",
        follow_redirects=False,
    ) as client:
        setup = await client.get("/setup")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', setup.text)
        assert csrf is not None
        response = await client.post(
            "/setup",
            data={
                "username": "host-admin",
                "password": "a long local-only password",
                "csrf_token": csrf.group(1),
                "interface_mode": "web",
                "source_mode": "openwebui",
                "source_name": "Product knowledge",
                "source_location": "http://127.0.0.1:3000",
                "credential_ref": "",
            },
        )

    repository = SQLiteSourceProfileRepository(database)
    try:
        profiles = repository.list()
    finally:
        repository.close()
    assert response.status_code == 303
    assert profiles[0].credential_ref is None
    assert profiles[0].capability_status == "connection_required"


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
