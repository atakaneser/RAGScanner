import re
from pathlib import Path

import httpx
import pytest
from ragscanner.api import create_app


@pytest.mark.anyio
async def test_dashboard_renders_and_queues_local_scan_with_csrf(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.md"
    source.write_text("# Synthetic dashboard source", encoding="utf-8")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/")
        css = await client.get("/dashboard-assets/dashboard.css")
        invalid = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": "invalid-dashboard-token",
                "path": str(source),
                "idempotency_key": "dashboard:invalid:001",
            },
        )
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        request_id = re.search(r'name="idempotency_key" value="([^"]+)"', dashboard.text)
        assert csrf is not None and request_id is not None
        queued = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "path": str(source),
                "idempotency_key": request_id.group(1),
                "scan_consent": "true",
            },
        )
        refreshed = await client.get("/")

    assert dashboard.status_code == 200
    assert "RAGScanner" in dashboard.text
    assert "Recent scans" in dashboard.text
    assert "Durable jobs" in dashboard.text
    assert "New scan" in dashboard.text
    assert css.status_code == 200
    assert invalid.status_code == 403
    assert queued.status_code == 303
    assert queued.headers["location"] == "/?notice=scan-queued"
    assert source.name in refreshed.text


@pytest.mark.anyio
async def test_dashboard_local_form_requires_explicit_scan_consent(tmp_path: Path) -> None:
    source = tmp_path / "knowledge.md"
    source.write_text("# Synthetic dashboard source", encoding="utf-8")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        request_id = re.search(r'name="idempotency_key" value="([^"]+)"', dashboard.text)
        assert csrf is not None and request_id is not None
        response = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "path": str(source),
                "idempotency_key": request_id.group(1),
            },
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/?notice=invalid-scan"


@pytest.mark.anyio
async def test_dashboard_openwebui_form_requires_explicit_content_consent(tmp_path: Path) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/")
        tokens = re.findall(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        request_ids = re.findall(r'name="idempotency_key" value="([^"]+)"', dashboard.text)
        response = await client.post(
            "/dashboard/scans/openwebui",
            data={
                "csrf_token": tokens[-1],
                "idempotency_key": request_ids[-1],
                "base_url": "http://127.0.0.1:3000",
                "knowledge_id": "kb-1",
                "credential_ref": "env:OPENWEBUI_API_KEY",
            },
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/?notice=invalid-scan"
