import asyncio
import json

import httpx
import pytest
from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.ai_analysis.service import build_analysis_request
from ragscanner.providers import (
    PROVIDER_CATALOG,
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
    create_analysis_provider,
)
from ragscanner.reporting import HtmlReporter


def test_analysis_request_excludes_raw_evidence(report, finding) -> None:
    item = finding("a")
    item.evidence = "raw document text must not leave the machine"
    request = build_analysis_request(report("scan-a", findings=[item]))

    encoded = json.dumps(request.context)
    assert "raw document text" not in encoded
    assert item.recommendation in encoded
    assert request.finding_ids == {"finding-a"}


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
    assert "runtime-key" not in config.model_dump_json()


def test_ollama_validates_referenced_finding_ids(report, finding, monkeypatch) -> None:
    adapter = OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="llama3")

    async def fake_post(*_args, **_kwargs):
        return {
            "message": {
                "content": json.dumps(
                    {"executive_summary": "Review now.", "finding_ids": ["other"]}
                )
            }
        }

    monkeypatch.setattr(adapter, "_post", fake_post)
    with pytest.raises(ModelProviderError, match="referenced findings") as captured:
        asyncio.run(
            adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")])))
        )
    assert captured.value.code == "ai_output_unknown_finding"


def test_ollama_discovers_installed_models(monkeypatch) -> None:
    adapter = OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="inventory")

    async def fake_request(*_args, **_kwargs):
        return {"models": [{"name": "llama3.1:8b"}, {"name": "qwen3:8b"}]}

    monkeypatch.setattr(adapter, "_request", fake_request)
    assert asyncio.run(adapter.list_models()) == ["llama3.1:8b", "qwen3:8b"]


def test_openai_compatible_adds_local_provenance(report, finding, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(
        base_url="http://127.0.0.1:8000", model="test-model", api_key="test-key"
    )

    async def fake_post(*_args, **_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "executive_summary": "Review finding.",
                                "priority_actions": ["Fix it"],
                                "finding_ids": ["finding-a"],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(adapter, "_post", fake_post)
    enriched = report("scan-a", findings=[finding("a")]).model_copy(
        update={
            "ai_analysis": asyncio.run(
                adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")])))
            )
        }
    )
    assert enriched.ai_analysis is not None
    assert enriched.ai_analysis.provider == "openai-compatible"
    assert "AI analysis" in HtmlReporter().render(enriched)


@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"executive_summary":"Review now.","finding_ids":[]}\n```',
        '{"analysis":{"summary":"Review now.","priorityActions":"Fix it",'
        '"findingIds":[]}} trailing prose',
    ],
)
def test_provider_recovers_common_structured_output_formatting_drift(
    report, monkeypatch, content
) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))

    assert analysis.executive_summary == "Review now."
    if "priorityActions" in content:
        assert analysis.priority_actions == ["Fix it"]


def test_provider_still_rejects_non_json_analysis(report, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):
        return {"choices": [{"message": {"content": "not structured output"}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    with pytest.raises(ModelProviderError) as captured:
        asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))
    assert captured.value.code == "ai_output_invalid"


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
