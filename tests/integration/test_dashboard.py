import os
import re
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from ragscanner.ai_analysis.models import AIReportAnalysis
from ragscanner.api import create_app
from ragscanner.application import JobApplicationService, resolve_secret_reference
from ragscanner.jobs import JobStatus
from ragscanner.onboarding import KnowledgeBaseCandidate, RAGEnvironmentCandidate
from ragscanner.quality import RAGConfigurationAdvice, RAGProfile
from ragscanner.storage import (
    MachineSecretStore,
    SourceProfile,
    SQLiteJobRepository,
    SQLiteSourceProfileRepository,
)
from ragscanner.web.dashboard import _score_band


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "unassessed"),
        (85, "healthy"),
        (84.99, "warning"),
        (70, "warning"),
        (69.99, "poor"),
        (55, "poor"),
        (54.99, "critical"),
    ],
)
def test_score_bands_match_product_thresholds(value, expected) -> None:  # type: ignore[no-untyped-def]
    assert _score_band(value) == expected


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
        sources_page = await client.get("/sources")
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
        assert 'id="icon-shield-check"' in dashboard.text
        assert "Scan jobs" in dashboard.text
        assert 'href="/settings"' in dashboard.text
        assert 'href="/settings#ai-settings"' not in dashboard.text
        assert 'href="/sources#integrations"' not in dashboard.text
        assert 'data-source-choice="website"' in sources_page.text
        assert 'data-source-choice="sharepoint"' in sources_page.text
        queued = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "path": str(source),
                "idempotency_key": request_id.group(1),
                "scan_consent": "true",
                "rag_profile": "policy_procedure",
                "embedding_context_tokens": "8192",
                "generator_context_tokens": "32768",
                "retrieval_top_k": "6",
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
    assert "Add AI guidance" in dashboard.text
    assert "NVIDIA NIM" in dashboard.text
    assert "Refresh models" in dashboard.text
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
    assert "Değerlendirilen boyutların ağırlıklı sonucu" in i18n.text
    assert "AI sağlayıcısı {seconds} saniye içinde yanıt vermedi" in i18n.text
    for translated_rule_title in (
        "Prompt injection talimatı",
        "Prompt-Injection-Anweisung",
        "Instruction d’injection de prompt",
        "提示词注入指令",
        "Istruzione di prompt injection",
    ):
        assert translated_rule_title in i18n.text
    for translated_quality_title in (
        "Aşırı Örtüşme",
        "Übermäßige Überlappung",
        "Chevauchement excessif",
        "重叠过多",
        "Sovrapposizione eccessiva",
    ):
        assert translated_quality_title in i18n.text
    for translated_duplicate_section in (
        "Yinelenen içerik karşılaştırmaları",
        "Duplikatvergleiche",
        "Comparaisons des doublons",
        "重复内容对比",
        "Confronti dei duplicati",
    ):
        assert translated_duplicate_section in i18n.text
    for translated_rag_reason in (
        "Neden bu aralık?",
        "Warum dieser Bereich?",
        "Pourquoi cette plage ?",
        "为何采用此范围？",
        "Perché questo intervallo?",
    ):
        assert translated_rag_reason in i18n.text
    for translated_password_action in (
        "Yönetici şifresini değiştir",
        "Administratorkennwort ändern",
        "Modifier le mot de passe administrateur",
        "更改管理员密码",
        "Cambia password amministratore",
    ):
        assert translated_password_action in i18n.text
    for translated_setup_privacy in (
        "API anahtarı çalışan makine servisinin belleğinde kalır",
        "Der API-Schlüssel bleibt im Speicher des laufenden Rechnerdienstes",
        "La clé API reste en mémoire dans le service actif",
        "API 密钥仅保留在当前计算机服务的内存中",
        "La chiave API rimane nella memoria del servizio in esecuzione",
    ):
        assert translated_setup_privacy in i18n.text
    for translated_download_action in (
        "Raporu indir",
        "Bericht herunterladen",
        "Télécharger le rapport",
        "下载报告",
        "Scarica rapporto",
    ):
        assert translated_download_action in i18n.text
    assert "Planlı tarama güncellendi." in i18n.text
    assert invalid.status_code == 403
    assert queued.status_code == 303
    assert queued.headers["location"] == "/jobs?notice=scan-queued"
    assert executed.status_code == 303
    assert executed.headers["location"] == "/?notice=job-completed"
    assert source.name in refreshed.text
    assert "completed" in refreshed.text
    assert 'class="recent-job-list"' in refreshed.text
    assert 'class="recent-job-card"' in refreshed.text
    repository = SQLiteJobRepository(database)
    try:
        payload = repository.list(limit=1).items[0].payload
    finally:
        repository.close()
    assert payload["rag"] == {
        "profile": "policy_procedure",
        "embedding_context_tokens": 8192,
        "generator_context_tokens": 32768,
        "retrieval_top_k": 6,
    }


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
async def test_dashboard_enqueues_website_job_and_deletes_saved_report(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "knowledge.md"
    source.write_text("# Synthetic website report", encoding="utf-8")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        dashboard = await client.get("/")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', dashboard.text)
        assert csrf is not None
        website = await client.post(
            "/dashboard/scans/website",
            data={
                "csrf_token": csrf.group(1),
                "idempotency_key": "dashboard-website-test-001",
                "url": "https://docs.example.test/sitemap.xml",
                "source_name": "Product website",
                "content_consent": "true",
            },
        )
        local = await client.post(
            "/dashboard/scans/local",
            data={
                "csrf_token": csrf.group(1),
                "idempotency_key": "dashboard-report-delete-001",
                "path": str(source),
                "scan_consent": "true",
            },
        )
        assert local.status_code == 303
        await client.post("/dashboard/worker/run-once", data={"csrf_token": csrf.group(1)})
        reports = await client.get("/reports")
        history_id = re.search(
            r'data-delete-url="/dashboard/reports/([a-f0-9]+)/delete"', reports.text
        )
        assert history_id is not None
        deleted = await client.post(
            f"/dashboard/reports/{history_id.group(1)}/delete",
            data={"csrf_token": csrf.group(1)},
        )
        missing = await client.get(f"/reports/{history_id.group(1)}")

    assert website.status_code == 303
    assert website.headers["location"] == "/jobs?notice=scan-queued"
    repository = SQLiteJobRepository(database)
    try:
        website_job = next(
            job
            for job in repository.list(limit=10).items
            if job.payload["source_kind"] == "website"
        )
        assert website_job.payload["website_url"] == "https://docs.example.test/sitemap.xml"
    finally:
        repository.close()
    assert deleted.headers["location"] == "/reports?notice=report-deleted"
    assert missing.status_code == 404


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

    located = finding("a")
    located.source = "policy-tr.pdf"
    located.page = 4
    located.line_start = 18
    located.line_end = 18
    located.evidence_highlight = "MFA'yı devre dışı bırak"
    history = SQLiteScanHistoryRepository(database)
    try:
        baseline_report = report("scan-a", findings=[located], overall=80).model_copy(
            update={
                "ai_analysis": AIReportAnalysis(
                    ai_analysis="The scan has one medium finding in the evaluated scope.",
                    root_causes=[
                        {
                            "pattern": "other",
                            "label": "Source policy",
                            "finding_rules": ["RULE-a"],
                            "example_files": ["policy-tr.pdf"],
                            "explanation": "The supplied evidence requires a policy decision.",
                            "confidence": "likely",
                        }
                    ],
                    priority_actions=[
                        {
                            "order": 1,
                            "action": "Review the source policy.",
                            "target": "corpus",
                            "addresses": ["RULE-a"],
                            "expected_effect": "Clarifies the deterministic finding.",
                            "effort": "low",
                        }
                    ],
                    review_questions=[
                        {
                            "question": "Who owns this policy?",
                            "informs": "The remediation owner.",
                        }
                    ],
                    score_commentary="The overall score reflects the supplied finding.",
                    coverage_caveat=None,
                    provider="ollama",
                    model="synthetic-model",
                    remote=False,
                ),
                "rag_configuration_advice": RAGConfigurationAdvice(
                    profile=RAGProfile.POLICY_PROCEDURE,
                    configured={"target_tokens": 300},
                    recommended={
                        "minimum_tokens": 80,
                        "target_tokens": 450,
                        "maximum_tokens": 700,
                        "overlap_tokens": 45,
                        "retrieval_top_k": 6,
                        "why": "Procedures need enough neighboring steps and heading context to remain actionable.",
                    },
                    observed={"median_chunk_tokens": 220, "chunks": 12},
                    actions=["Benchmark representative policy questions."],
                    validation_metrics=["Recall@k"],
                ),
            }
        )
        baseline = history.save(baseline_report)
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
        client.cookies.set("ragscanner_locale", "tr")
        html_export = await client.get(f"/reports/{baseline}/download/html")
        excel_export = await client.get(f"/reports/{baseline}/download/xlsx")
        pdf_export = await client.get(f"/reports/{baseline}/download/pdf")
        invalid_export = await client.get(f"/reports/{baseline}/download/csv")
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
    assert "policy-tr.pdf" in detail.text
    assert "Page</span> 4" in detail.text
    assert "Line</span> 18" in detail.text
    assert "Download report" in detail.text
    assert "Root cause analysis" in detail.text
    assert "Score commentary" in detail.text
    assert "Review the source policy." in detail.text
    assert "Who owns this policy?" in detail.text
    assert "Recommended chunk size" in detail.text
    assert "450 tokens" in detail.text
    assert "Why this range?" in detail.text
    assert f"/reports/{baseline}/download/html" in detail.text
    assert html_export.status_code == 200
    assert html_export.headers["content-type"].startswith("text/html")
    assert "Yönetici özeti" in html_export.text
    assert "attachment; filename=" in html_export.headers["content-disposition"]
    assert excel_export.status_code == 200
    assert excel_export.content.startswith(b"PK")
    assert excel_export.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert pdf_export.status_code == 200
    assert pdf_export.content.startswith(b"%PDF-")
    assert invalid_export.status_code == 422
    assert "<mark>MFA&#39;yı devre dışı bırak</mark>" in detail.text
    assert "· <span>completed</span>" in detail.text
    assert "score-warning" in detail.text
    assert 'class="finding" open' in detail.text
    assert "Report comparison" in comparison.text
    assert "A scan job tells RAGScanner what source to scan" in jobs.text
    assert "How do you want to choose the source?" in jobs.text
    assert "Use a connected source" in jobs.text
    assert "Enter source manually" in jobs.text
    assert "First run date and time" in jobs.text
    assert "Available models" in jobs.text
    assert 'data-form-step="4"' in jobs.text
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
        assert "Models available on this machine" in page.text
        assert "data-default-ai-inventory" in page.text
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
async def test_dashboard_repairs_stale_source_secret_reference_after_data_migration(
    tmp_path: Path,
) -> None:
    database = tmp_path / "current" / "history.sqlite3"
    old_store = MachineSecretStore(tmp_path / "previous")
    stale_reference = old_store.save("source-migrated", "synthetic-migrated-key")
    current_store = MachineSecretStore(database.parent)
    current_store.root.mkdir(parents=True)
    (old_store.root / "source-migrated").replace(current_store.root / "source-migrated")
    repository = SQLiteSourceProfileRepository(database)
    try:
        profile = repository.save(
            SourceProfile(
                name="Migrated OpenWebUI",
                kind="openwebui",
                base_url="http://127.0.0.1:3000",
                credential_ref=stale_reference,
            )
        )
    finally:
        repository.close()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(database)),
        base_url="http://testserver",
    ) as client:
        page = await client.get("/sources")

    repository = SQLiteSourceProfileRepository(database)
    try:
        repaired = repository.get(profile.id)
    finally:
        repository.close()
    assert page.status_code == 200
    assert "Migrated OpenWebUI · Ready" in page.text
    assert repaired is not None and repaired.credential_ref != stale_reference
    assert resolve_secret_reference(repaired.credential_ref or "") == "synthetic-migrated-key"


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
                "schedule_start_at": "2026-07-24T06:15:00Z",
            },
        )
        refreshed = await client.get("/jobs")
        schedule_id = re.search(r"/dashboard/schedules/([a-f0-9]{32})/update", refreshed.text)
        assert schedule_id is not None
        updated = await client.post(
            f"/dashboard/schedules/{schedule_id.group(1)}/update",
            data={
                "csrf_token": csrf.group(1),
                "name": "Weekly support health",
                "interval_minutes": "10080",
                "next_run_at": "2026-08-01T07:30:00+03:00",
            },
        )
        updated_page = await client.get("/jobs")

    assert saved.headers["location"] == "/jobs?notice=schedule-saved"
    assert "Daily support health" in refreshed.text
    assert "2026-07-24T06:15:00+00:00" in refreshed.text
    assert "RAGSCH-0001" in refreshed.text
    assert "RAGSCN-" not in refreshed.text
    assert updated.headers["location"] == "/jobs?notice=schedule-updated"
    assert "Weekly support health" in updated_page.text
    assert "2026-08-01T04:30:00+00:00" in updated_page.text
