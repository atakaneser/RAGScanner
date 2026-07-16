import re
from pathlib import Path

import httpx
import pytest
from ragscanner.api import create_app
from ragscanner.onboarding import KnowledgeBaseCandidate, RAGEnvironmentCandidate


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
        i18n = await client.get("/dashboard-assets/dashboard-i18n.js")
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
        executed = await client.post(
            "/dashboard/worker/run-once",
            data={"csrf_token": csrf.group(1)},
        )
        refreshed = await client.get("/")

    assert dashboard.status_code == 200
    assert "RAGScanner" in dashboard.text
    assert "Recent reports" in dashboard.text
    assert "Recent jobs" in dashboard.text
    assert "Create job" in dashboard.text
    assert "Add AI analysis to this report" in dashboard.text
    assert "NVIDIA NIM" in dashboard.text
    assert "Detect available models" in dashboard.text
    assert css.status_code == 200
    assert i18n.status_code == 200
    assert 'data-language-picker aria-label="Language"' in dashboard.text
    for locale in ("English", "Türkçe", "Deutsch", "Français", "简体中文", "Italiano"):
        assert locale in dashboard.text
    assert '"Overview": "Genel Bakış"' in i18n.text
    assert '"Overview": "Übersicht"' in i18n.text
    assert '"Overview": "Vue d’ensemble"' in i18n.text
    assert '"Overview": "概览"' in i18n.text
    assert '"Overview": "Panoramica"' in i18n.text
    assert invalid.status_code == 403
    assert queued.status_code == 303
    assert queued.headers["location"] == "/?notice=scan-queued"
    assert executed.status_code == 303
    assert executed.headers["location"] == "/?notice=job-completed"
    assert source.name in refreshed.text
    assert "completed" in refreshed.text


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


@pytest.mark.anyio
async def test_dashboard_discovers_local_environments_and_openwebui_knowledge_bases(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "ragscanner.web.dashboard.discover_local_rag_environments",
        lambda **kwargs: [
            RAGEnvironmentCandidate(
                platform="openwebui",
                base_url="http://127.0.0.1:3000",
                discovery_status="reachable",
                runtime="docker",
                metadata_inventory_supported=True,
            )
        ],
    )
    monkeypatch.setattr(
        "ragscanner.web.dashboard.resolve_secret_reference", lambda reference: "synthetic-api-key"
    )
    monkeypatch.setattr(
        "ragscanner.web.dashboard.discover_openwebui_knowledge_bases",
        lambda base_url, api_key: [
            KnowledgeBaseCandidate(id="kb-1", name="Engineering", description="Synthetic")
        ],
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path / "history.sqlite3")),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        assert csrf is not None
        denied = await client.post(
            "/dashboard/discovery/environments", data={"csrf_token": csrf.group(1)}
        )
        environments = await client.post(
            "/dashboard/discovery/environments",
            data={"csrf_token": csrf.group(1), "metadata_consent": "true"},
        )
        knowledge_bases = await client.post(
            "/dashboard/discovery/openwebui/knowledge-bases",
            data={
                "csrf_token": csrf.group(1),
                "base_url": "http://127.0.0.1:3000",
                "credential_ref": "env:OPENWEBUI_API_KEY",
            },
        )

    assert denied.status_code == 400
    assert environments.json()["environments"][0]["platform"] == "openwebui"
    assert knowledge_bases.json()["knowledge_bases"] == [
        {"id": "kb-1", "name": "Engineering", "description": "Synthetic"}
    ]


@pytest.mark.anyio
async def test_dashboard_sources_reports_detail_and_comparison_are_real_pages(
    tmp_path: Path, report, finding
) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    from ragscanner.storage import SQLiteScanHistoryRepository

    history = SQLiteScanHistoryRepository(database)
    try:
        baseline = history.save(report("scan-a", findings=[finding("a")]))
        candidate = history.save(report("scan-b", findings=[finding("b")]))
    finally:
        history.close()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        overview = await client.get("/")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', overview.text)
        assert csrf is not None
        saved = await client.post(
            "/dashboard/sources",
            data={
                "csrf_token": csrf.group(1),
                "name": "Local OpenWebUI",
                "kind": "openwebui",
                "location": "http://127.0.0.1:3000",
                "credential_ref": "env:OPENWEBUI_API_KEY",
            },
        )
        sources = await client.get("/sources")
        refreshed_overview = await client.get("/")
        reports = await client.get("/reports", params={"from": "2026-07-01", "to": "2026-07-31"})
        detail = await client.get(f"/reports/{baseline}")
        comparison = await client.get(
            "/compare", params={"baseline": baseline, "candidate": candidate}
        )
        jobs = await client.get("/jobs")
        settings = await client.get("/settings")

    assert saved.status_code == 303
    assert "Local OpenWebUI" in sources.text
    assert "Local OpenWebUI · scan ready" in refreshed_overview.text
    assert "Select exactly two reports" in reports.text
    assert "Finding a" in detail.text
    assert "Report comparison" in comparison.text
    assert "Create, monitor, cancel" in jobs.text
    assert "versioned SQLite snapshots" in settings.text
