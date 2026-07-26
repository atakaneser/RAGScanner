"""Optional AI analysis contracts and provider compatibility tests."""

import asyncio
import json

import httpx
import pytest
from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.ai_analysis.prompt import system_prompt
from ragscanner.ai_analysis.service import build_analysis_request
from ragscanner.application.static_scan import StaticScanApplicationService
from ragscanner.providers import (
    PROVIDER_CATALOG,
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
    create_analysis_provider,
)
from ragscanner.reporting import HtmlReporter


def _analysis_payload(
    analysis: str = "The evaluated scan contains no deterministic severity findings.",
    *,
    caveat: str | None = None,
) -> dict[str, object]:
    return {
        "ai_analysis": analysis,
        "root_causes": [],
        "priority_actions": [
            {
                "order": 1,
                "action": "Review the deterministic report.",
                "target": "configuration",
                "addresses": [],
                "expected_effect": "Confirms the configured scan scope.",
                "effort": "low",
            }
        ],
        "review_questions": [
            {
                "question": "Does this scope match the production corpus?",
                "informs": "The next scan configuration.",
            }
        ],
        "score_commentary": "The supplied overall score is scoped to evaluated checks.",
        "coverage_caveat": caveat,
    }


def test_analysis_request_includes_only_bounded_redacted_group_evidence(report, finding) -> None:
    items = []
    for index in range(12):
        item = finding(chr(97 + index))
        item.source = f"source-{index}.pdf"
        item.page = index + 1
        item.line_start = 10
        item.line_end = 12
        item.evidence = "Token sk-secretvalue1234567890 " + "bounded source text " * 100
        item.metadata["labels"] = ["procedure"]
        items.append(item)
    request = build_analysis_request(report("scan-a", findings=items))

    encoded = json.dumps(request.context)
    assert "sk-secretvalue1234567890" not in encoded
    assert "[REDACTED]" in encoded
    assert "source-0.pdf" in encoded
    assert request.context["findings"][0]["evidence"][0]["lines"] == "10-12"
    assert all(len(group["evidence"]) <= 10 for group in request.context["findings"])


def test_system_prompt_uses_runtime_report_language() -> None:
    prompt = system_prompt("tr")
    assert "Write ALL free-text output in Turkish" in prompt
    assert "{report_language}" not in prompt


def test_remote_provider_requires_explicit_consent() -> None:
    with pytest.raises(ValueError, match="consent-remote"):
        OllamaAnalysisProvider(base_url="https://model.example.test", model="local")
    with pytest.raises(ValueError, match="HTTPS"):
        OllamaAnalysisProvider(
            base_url="http://model.example.test", model="local", consent_remote=True
        )


def test_provider_catalog_covers_common_local_and_remote_services() -> None:
    provider_ids = {item.id for item in PROVIDER_CATALOG}
    assert {"ollama", "lm-studio", "localai", "vllm"} <= provider_ids
    assert {"openrouter", "openai", "nvidia-nim", "anthropic", "google-gemini"} <= provider_ids


def test_scan_ai_config_requires_remote_consent_and_never_contains_a_secret() -> None:
    with pytest.raises(ValueError, match="explicit consent"):
        AIProviderConfig(enabled=True, provider="openrouter", model="model")
    config = AIProviderConfig(
        enabled=True,
        provider="openrouter",
        model="model",
        credential_ref="env:OPENROUTER_API_KEY",
        remote_consent=True,
    )
    provider = create_analysis_provider(config, secret_resolver=lambda _reference: "runtime-key")
    assert provider.provider_id == "openrouter"
    assert provider.timeout_seconds == 180
    assert "runtime-key" not in config.model_dump_json()


def test_ollama_discovers_installed_models(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    adapter = OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="inventory")

    async def fake_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"models": [{"name": "llama3.1:8b"}, {"name": "qwen3:8b"}]}

    monkeypatch.setattr(adapter, "_request", fake_request)
    assert asyncio.run(adapter.list_models()) == ["llama3.1:8b", "qwen3:8b"]


def test_openai_compatible_adds_local_provenance(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(
        base_url="http://127.0.0.1:8000", model="test-model", api_key="test-key"
    )

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps(_analysis_payload())}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    source_report = report("scan-a")
    enriched = source_report.model_copy(
        update={"ai_analysis": asyncio.run(adapter.analyze(build_analysis_request(source_report)))}
    )
    assert enriched.ai_analysis is not None
    assert enriched.ai_analysis.provider == "openai-compatible"
    assert "AI analysis" in HtmlReporter().render(enriched)


def test_rule_addressed_priority_action_is_attached_to_matching_findings(
    report, finding, monkeypatch
) -> None:
    item = finding("a")
    payload = _analysis_payload()
    priority_actions = payload["priority_actions"]
    assert isinstance(priority_actions, list)
    first_action = priority_actions[0]
    assert isinstance(first_action, dict)
    first_action["addresses"] = ["RULE-a"]
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    source_report = report("scan-a", findings=[item])
    analysis = asyncio.run(adapter.analyze(build_analysis_request(source_report)))
    assert [action.finding_id for action in analysis.finding_actions] == [item.id]
    assert analysis.finding_actions[0].remediation == "Review the deterministic report."


def test_provider_accepts_one_optional_json_fence(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    content = f"```json\n{json.dumps(_analysis_payload())}\n```"

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))
    assert analysis.ai_analysis.startswith("The evaluated scan")


def test_common_local_model_shape_variations_are_safely_normalized(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    supplied = {
        "summary": "Tarama bulguları için veri alımı ayarları gözden geçirilmelidir.",
        "root_causes": {
            "pattern": "boilerplate_duplication",
            "name": "Şablon tekrarı",
            "rules": "QUALITY-EXACT-DUPLICATE-CHUNK",
            "files": "policy.pdf",
            "description": "Aynı şablon metni birden fazla dosyada bulunuyor.",
            "confidence": "olası",
        },
        "priority_actions": {
            "recommendation": "Üstbilgileri veri alımı sırasında ayırın.",
            "target": "veri alımı",
            "effort": "düşük",
        },
        "review_questions": "Üstbilgiler arama için gerekli mi?",
        "unexpected_local_model_field": "ignored",
    }
    payload = {"result": supplied}
    requests = 0

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal requests
        requests += 1
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    request = build_analysis_request(report("scan-a"), output_language="tr")
    analysis = asyncio.run(adapter.analyze(request))

    assert requests == 1
    assert analysis.ai_analysis == supplied["summary"]
    assert analysis.score_commentary == supplied["summary"]
    assert analysis.root_causes[0].pattern == "P1"
    assert analysis.root_causes[0].confidence == "likely"
    assert analysis.priority_actions[0].target == "ingestion"
    assert analysis.priority_actions[0].effort == "low"
    assert analysis.review_questions[0].informs == "İlgili düzeltme kararı."


def test_invalid_json_retries_once_with_strict_instruction(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    payloads: list[dict[str, object]] = []

    async def fake_post(_path, payload, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        payloads.append(payload)
        content = "not json" if len(payloads) == 1 else json.dumps(_analysis_payload())
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))

    assert analysis.ai_analysis.startswith("The evaluated scan")
    assert len(payloads) == 2
    retry_messages = payloads[1]["messages"]
    assert retry_messages[-1]["content"] == "Return only the JSON object, nothing else."
    assert payloads[0]["temperature"] == 0.1


def test_second_invalid_json_returns_stable_error(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": "not structured output"}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    with pytest.raises(ModelProviderError) as captured:
        asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))
    assert captured.value.code == "ai_output_invalid"
    assert captured.value.detail_code == "invalid_json"


def test_second_invalid_output_keeps_findings_and_uses_localized_fallback(
    report, finding, monkeypatch
) -> None:
    class InvalidProvider:
        async def analyze(self, _request):  # type: ignore[no-untyped-def]
            raise ModelProviderError(
                "ai_output_invalid",
                "The model returned analysis that did not match the schema.",
            )

    monkeypatch.setattr(
        "ragscanner.application.static_scan.create_analysis_provider",
        lambda *_args, **_kwargs: InvalidProvider(),
    )
    item = finding("a")
    source_report = report("scan-a", findings=[item])
    config = AIProviderConfig(
        enabled=True,
        provider="ollama",
        model="installed-model",
        output_language="tr",
    )

    enriched = asyncio.run(StaticScanApplicationService._enrich_async(source_report, config))
    assert enriched.findings == source_report.findings
    assert enriched.ai_analysis is None
    assert enriched.ai_analysis_error_code == "ai_output_invalid"
    assert enriched.ai_analysis_error == "AI analizi üretilemedi."


def test_invalid_output_fallback_explains_the_safe_failure_stage(report, monkeypatch) -> None:
    class InvalidProvider:
        async def analyze(self, _request):  # type: ignore[no-untyped-def]
            raise ModelProviderError(
                "ai_output_invalid",
                "The model did not return one valid JSON object.",
                detail_code="invalid_json",
            )

    monkeypatch.setattr(
        "ragscanner.application.static_scan.create_analysis_provider",
        lambda *_args, **_kwargs: InvalidProvider(),
    )
    source_report = report("scan-a")
    config = AIProviderConfig(
        enabled=True,
        provider="ollama",
        model="installed-model",
        output_language="tr",
    )

    enriched = asyncio.run(StaticScanApplicationService._enrich_async(source_report, config))
    assert enriched.ai_analysis_error_code == "ai_output_invalid"
    assert enriched.ai_analysis_error == (
        "AI analizi üretilemedi. Model iki denemede de geçerli JSON döndürmedi."
    )


def test_severity_distribution_must_be_stated_without_low_only_framing(report, monkeypatch) -> None:
    source_report = report("scan-a").model_copy(
        update={
            "severity_summary": {
                "critical": 0,
                "high": 0,
                "medium": 3,
                "low": 24,
                "info": 0,
            }
        }
    )
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            _analysis_payload("The scan has 3 medium and 24 low findings.")
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(source_report)))
    assert "3 medium and 24 low" in analysis.ai_analysis


def test_missing_severity_distribution_is_added_from_verified_counts(report, monkeypatch) -> None:
    source_report = report("scan-a").model_copy(
        update={
            "severity_summary": {
                "critical": 0,
                "high": 0,
                "medium": 3,
                "low": 24,
                "info": 0,
            }
        }
    )
    payload = _analysis_payload("Tekrar bulguları verimlilik puanını etkiliyor.")
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    requests = 0

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal requests
        requests += 1
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    request = build_analysis_request(source_report, output_language="tr")
    analysis = asyncio.run(adapter.analyze(request))

    assert requests == 1
    assert analysis.ai_analysis.startswith("Önem dağılımı: 3 orta, 24 düşük.")


def test_coverage_caveat_names_every_unevaluated_area(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    payload = _analysis_payload(
        caveat="Scores reflect evaluated areas only; security was not evaluated."
    )

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    source_report = report("scan-a", coverage="not_assessed")
    analysis = asyncio.run(adapter.analyze(build_analysis_request(source_report)))
    assert analysis.coverage_caveat is not None
    assert "security" in analysis.coverage_caveat


def test_missing_coverage_caveat_is_added_from_verified_scope(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps(_analysis_payload())}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    source_report = report("scan-a", coverage="not_assessed")
    request = build_analysis_request(source_report, output_language="tr")
    analysis = asyncio.run(adapter.analyze(request))

    assert analysis.coverage_caveat is not None
    assert analysis.coverage_caveat == (
        "Puanlar yalnızca değerlendirilen alanları kapsar; değerlendirilmeyenler: security."
    )


def test_provider_http_failure_has_safe_stable_code(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    response = httpx.Response(
        401,
        request=httpx.Request("GET", "https://provider.example.test/v1/models"),
        text="synthetic sensitive provider detail",
    )

    class FakeClient:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            del args

        async def request(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            del args, kwargs
            return response

    monkeypatch.setattr(
        "ragscanner.providers.adapters.httpx.AsyncClient", lambda **_kwargs: FakeClient()
    )
    adapter = OpenAICompatibleAnalysisProvider(
        base_url="https://provider.example.test",
        model="model",
        api_key="synthetic-key",
        consent_remote=True,
    )

    with pytest.raises(ModelProviderError) as captured:
        asyncio.run(adapter.list_models())
    assert captured.value.code == "ai_provider_http_401"
    assert str(captured.value) == "The AI provider rejected the request with HTTP 401."
    assert "sensitive" not in str(captured.value)


@pytest.mark.parametrize("provider_kind", ["ollama", "openai-compatible"])
def test_analysis_retries_http_400_without_unsupported_structured_output(
    report, monkeypatch, provider_kind
) -> None:  # type: ignore[no-untyped-def]
    adapter = (
        OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="test-model")
        if provider_kind == "ollama"
        else OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    )
    payloads: list[dict[str, object]] = []

    async def fake_post(_path, payload, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        payloads.append(payload)
        if len(payloads) == 1:
            raise ModelProviderError("ai_provider_http_400", "Synthetic HTTP 400")
        content = json.dumps(_analysis_payload())
        return (
            {"message": {"content": content}}
            if provider_kind == "ollama"
            else {"choices": [{"message": {"content": content}}]}
        )

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))

    assert analysis.ai_analysis.startswith("The evaluated scan")
    if provider_kind == "ollama":
        assert payloads[1]["format"] == "json"
    else:
        assert "response_format" not in payloads[1]
