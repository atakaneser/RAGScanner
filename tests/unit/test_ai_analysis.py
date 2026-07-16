import asyncio
import json

import pytest
from ragscanner.ai_analysis.service import build_analysis_request
from ragscanner.providers import (
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
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


def test_ollama_validates_referenced_finding_ids(report, finding, monkeypatch) -> None:
    adapter = OllamaAnalysisProvider(base_url="http://127.0.0.1:11434", model="llama3")

    async def fake_post(*_args, **_kwargs):
        return {"message": {"content": json.dumps({"executive_summary": "Review now.", "finding_ids": ["other"]})}}

    monkeypatch.setattr(adapter, "_post", fake_post)
    with pytest.raises(ModelProviderError, match="finding IDs"):
        asyncio.run(adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")]))) )


def test_openai_compatible_adds_local_provenance(report, finding, monkeypatch) -> None:
    adapter = OpenAICompatibleAnalysisProvider(
        base_url="http://127.0.0.1:8000", model="test-model", api_key="test-key"
    )

    async def fake_post(*_args, **_kwargs):
        return {"choices": [{"message": {"content": json.dumps({"executive_summary": "Review finding.", "priority_actions": ["Fix it"], "finding_ids": ["finding-a"]})}}]}

    monkeypatch.setattr(adapter, "_post", fake_post)
    enriched = report("scan-a", findings=[finding("a")]).model_copy(
        update={"ai_analysis": asyncio.run(adapter.analyze(build_analysis_request(report("scan-a", findings=[finding("a")]))) )}
    )
    assert enriched.ai_analysis is not None
    assert enriched.ai_analysis.provider == "openai-compatible"
    assert "AI analysis" in HtmlReporter().render(enriched)
