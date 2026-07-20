import os
import re
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from ragscanner.api import create_app
from ragscanner.application import JobApplicationService, resolve_secret_reference
from ragscanner.jobs import JobStatus
from ragscanner.onboarding import KnowledgeBaseCandidate, RAGEnvironmentCandidate
from ragscanner.storage import SQLiteJobRepository


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
    assert "RAGScanner service is running" in dashboard.text
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
    assert queued.headers["location"] == "/jobs?notice=scan-queued"
    assert executed.status_code == 303
    assert executed.headers["location"] == "/?notice=job-completed"
    assert source.name in refreshed.text
    assert "completed" in refreshed.text
    assert 'class="recent-job-list"' in refreshed.text
    assert 'class="recent-job-card"' in refreshed.text


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
async def test_dashboard_lists_every_detected_ai_model_and_keeps_direct_key_out_of_jobs(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.md"
    source.write_text("# Synthetic dashboard source", encoding="utf-8")
    captured = {}
    existing_ai_names = {name for name in os.environ if name.startswith("RAGSCANNER_AI_")}

    async def models(config, *, secret_resolver):  # type: ignore[no-untyped-def]
        captured["config"] = config
        captured["secret_resolver"] = secret_resolver
        return ["model-a", "model-b", "model-c"]

    monkeypatch.setattr("ragscanner.web.dashboard.discover_provider_models", models)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/jobs")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        request_id = re.search(r'name="idempotency_key" value="([^"]+)"', dashboard.text)
        assert csrf is not None and request_id is not None
        discovered = await client.post(
            "/dashboard/discovery/ai-models",
            data={
                "csrf_token": csrf.group(1),
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api",
                "api_key": "synthetic-dashboard-ai-key",
                "remote_consent": "true",
            },
        )
        queued = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "path": str(source),
                "idempotency_key": request_id.group(1),
                "scan_consent": "true",
                "ai_enabled": "true",
                "ai_provider": "openrouter",
                "ai_model": "model-b",
                "ai_base_url": "https://openrouter.ai/api",
                "ai_api_key": "synthetic-dashboard-ai-key",
                "ai_remote_consent": "true",
            },
        )

    try:
        assert discovered.json() == {"models": ["model-a", "model-b", "model-c"]}
        assert captured["config"].credential_ref.startswith("file-secret:")
        with pytest.raises(ValueError, match="unavailable"):
            resolve_secret_reference(captured["config"].credential_ref)
        assert "data-ai-model-results" in dashboard.text
        assert queued.status_code == 303
        repository = SQLiteJobRepository(database)
        try:
            job = repository.list(limit=1).items[0]
        finally:
            repository.close()
        reference = job.payload["ai"]["credential_ref"]
        assert reference.startswith("file-secret:")
        assert resolve_secret_reference(reference) == "synthetic-dashboard-ai-key"
        assert "synthetic-dashboard-ai-key" not in job.model_dump_json()
        assert b"synthetic-dashboard-ai-key" not in database.read_bytes()
    finally:
        for name in [
            key
            for key in os.environ
            if key.startswith("RAGSCANNER_AI_") and key not in existing_ai_names
        ]:
            os.environ.pop(name, None)


@pytest.mark.anyio
async def test_dashboard_job_status_exposes_safe_failure_codes(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.md"
    source.write_text("# Synthetic dashboard source", encoding="utf-8")
    repository = SQLiteJobRepository(database)
    try:
        queued = JobApplicationService(repository).enqueue_local_scan(
            source, idempotency_key="dashboard:failure-log:001", max_attempts=1
        )
        claimed = repository.claim("test-worker", lease_duration=timedelta(seconds=30))
        assert claimed is not None and claimed.status is JobStatus.RUNNING
        repository.fail(
            queued.id,
            "test-worker",
            error_code="source_path_unreadable",
            error_message="The Host Service cannot read the selected source path.",
        )
    finally:
        repository.close()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)), base_url="http://testserver"
    ) as client:
        jobs_page = await client.get("/jobs")
        status = await client.get("/dashboard/jobs/status")

    assert "Job activity logs" in jobs_page.text
    assert "source_path_unreadable" in jobs_page.text
    assert status.json()["logs"][0]["code"] == "source_path_unreadable"
    assert status.json()["logs"][0]["message"] == (
        "The Host Service cannot read the selected source path."
    )


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
    assert "Local OpenWebUI · API key needed" in refreshed_overview.text
    assert "Select exactly two reports" in reports.text
    assert "RAGREP-0001" in reports.text
    assert "<td><strong>Knowledge</strong></td>" in reports.text
    assert "Finding a" in detail.text
    assert 'class="finding" open' in detail.text
    assert "Report comparison" in comparison.text
    assert "A scan job tells RAGScanner what source to scan" in jobs.text
    assert "versioned SQLite snapshots" in settings.text


@pytest.mark.anyio
async def test_dashboard_accepts_api_key_without_persisting_plaintext_and_unblocks_source(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    monkeypatch.setattr(
        "ragscanner.web.dashboard.discover_openwebui_knowledge_bases",
        lambda base_url, api_key: [
            KnowledgeBaseCandidate(
                id="kb-1", name="Engineering", description=base_url + api_key[:0]
            )
        ],
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        sources = await client.get("/sources")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', sources.text)
        assert csrf is not None
        saved = await client.post(
            "/dashboard/sources",
            data={
                "csrf_token": csrf.group(1),
                "name": "Local OpenWebUI",
                "kind": "openwebui",
                "location": "http://127.0.0.1:3000",
            },
        )
        refreshed = await client.get("/jobs")
        profile_id = re.search(
            r'data-connect-profile="([a-f0-9]{32})"', (await client.get("/sources")).text
        )
        assert profile_id is not None
        connected = await client.post(
            f"/dashboard/sources/{profile_id.group(1)}/connect",
            data={"csrf_token": csrf.group(1), "api_key": "synthetic-dashboard-secret"},
        )

    from ragscanner.storage import SQLiteSourceProfileRepository

    repository = SQLiteSourceProfileRepository(database)
    try:
        profile = repository.get(profile_id.group(1))
    finally:
        repository.close()

    assert saved.status_code == 303
    assert "Local OpenWebUI · API key needed" in refreshed.text
    source_option = re.search(
        r'<option value="[a-f0-9]{32}"[^>]*>Local OpenWebUI[^<]*</option>', refreshed.text
    )
    assert source_option is not None
    assert "disabled" not in source_option.group(0)
    assert connected.status_code == 200
    assert connected.json()["knowledge_bases"][0]["id"] == "kb-1"
    assert profile is not None
    assert profile.credential_ref is not None
    assert profile.credential_ref.startswith("file-secret:")
    assert resolve_secret_reference(profile.credential_ref) == "synthetic-dashboard-secret"
    assert "synthetic-dashboard-secret" not in database.read_bytes().decode(
        "utf-8", errors="ignore"
    )
    monkeypatch.delenv(profile.credential_ref.removeprefix("env:"), raising=False)


@pytest.mark.anyio
async def test_dashboard_settings_persist_language_and_machine_ai_credential(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        page = await client.get("/settings")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        assert csrf is not None
        saved = await client.post(
            "/dashboard/settings",
            data={
                "csrf_token": csrf.group(1),
                "locale": "tr",
                "timezone": "local",
                "report_detail": "detailed",
                "rows_per_page": "25",
                "ai_provider": "openrouter",
                "ai_model": "model-a",
                "ai_base_url": "https://openrouter.ai/api",
                "ai_api_key": "synthetic-persistent-ai-key",
                "ai_remote_consent": "true",
            },
        )

    from ragscanner.storage import SQLiteSourceProfileRepository

    repository = SQLiteSourceProfileRepository(database)
    try:
        settings = repository.dashboard_settings()
    finally:
        repository.close()
    assert saved.status_code == 303
    assert "ragscanner_locale=tr" in saved.headers["set-cookie"]
    assert settings.locale == "tr"
    assert settings.ai_credential_ref is not None
    assert resolve_secret_reference(settings.ai_credential_ref) == "synthetic-persistent-ai-key"
    assert b"synthetic-persistent-ai-key" not in database.read_bytes()


@pytest.mark.anyio
async def test_dashboard_creates_recurring_scan_separately_from_job_history(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.md"
    source.write_text("# Scheduled source", encoding="utf-8")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        page = await client.get("/jobs")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        request_id = re.search(r'name="idempotency_key" value="([^"]+)"', page.text)
        assert csrf is not None and request_id is not None
        saved = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "idempotency_key": request_id.group(1),
                "path": str(source),
                "source_name": "Support knowledge",
                "scan_consent": "true",
                "execution_mode": "scheduled",
                "schedule_name": "Daily support health",
                "interval_minutes": "1440",
            },
        )
        refreshed = await client.get("/jobs")

    assert saved.headers["location"] == "/jobs?notice=schedule-saved"
    assert "Daily support health" in refreshed.text
    assert "RAGSCH-0001" in refreshed.text
    assert "RAGSCN-" not in refreshed.text
