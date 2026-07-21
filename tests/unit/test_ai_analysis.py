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
    assert provider.timeout_seconds == 180
    assert "runtime-key" not in config.model_dump_json()

    slower = config.model_copy(update={"timeout_seconds": 300})
    slower_provider = create_analysis_provider(
        slower, secret_resolver=lambda _reference: "runtime-key"
    )
    assert slower_provider.timeout_seconds == 300


def test_ollama_ignores_unknown_finding_ids_without_discarding_valid_analysis(
    report, finding, monkeypatch
) -> None:
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
    analysis = asyncio.run(
        adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")])))
    )
    assert analysis.finding_ids == []
    assert analysis.ignored_finding_ids == ["other"]


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


def test_provider_normalizes_finding_actions_and_drops_only_unknown_references(
    report, finding, monkeypatch
) -> None:
    adapter = OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")

    async def fake_post(*_args, **_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Review now.",
                                "findingActions": [
                                    {
                                        "finding_id": "finding-a",
                                        "remediation": "Apply the documented control.",
                                        "verification_steps": ["Re-scan the source."],
                                    },
                                    {
                                        "finding_id": "invented",
                                        "remediation": "Do not show this.",
                                    },
                                ],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(
        adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")])))
    )
    assert [item.finding_id for item in analysis.finding_actions] == ["finding-a"]
    assert analysis.ignored_finding_ids == ["invented"]


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


@pytest.mark.parametrize("provider_kind", ["ollama", "openai-compatible"])
def test_analysis_retries_http_400_without_unsupported_structured_output(
    report, monkeypatch, provider_kind
) -> None:  # type: ignore[no-untyped-def]
    adapter = (
        OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="test-model")
        if provider_kind == "ollama"
        else OpenAICompatibleAnalysisProvider(base_url="http://127.0.0.1:8000", model="test-model")
    )
    payloads = []

    async def fake_post(_path, payload, *_args):  # type: ignore[no-untyped-def]
        payloads.append(payload)
        if len(payloads) == 1:
            raise ModelProviderError("ai_provider_http_400", "Synthetic HTTP 400")
        content = json.dumps({"executive_summary": "Review now.", "finding_ids": []})
        return (
            {"message": {"content": content}}
            if provider_kind == "ollama"
            else {"choices": [{"message": {"content": content}}]}
        )

    monkeypatch.setattr(adapter, "_post", fake_post)
    analysis = asyncio.run(adapter.analyze(build_analysis_request(report("scan-a"))))

    assert analysis.executive_summary == "Review now."
    if provider_kind == "ollama":
        assert payloads[1]["format"] == "json"
    else:
        assert "response_format" not in payloads[1]
