"""Consent-aware HTTP adapters for optional report enrichment."""

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from ragscanner.ai_analysis.models import (
    AIAnalysisContent,
    AIFindingAction,
    AIProviderConfig,
    AIReportAnalysis,
)
from ragscanner.ai_analysis.prompt import system_prompt
from ragscanner.ai_analysis.service import AnalysisRequest


class ModelProviderError(RuntimeError):
    """A safe, user-facing provider failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    name: str
    default_base_url: str
    local: bool
    protocol: str = "openai"
    credential_required: bool = True


PROVIDER_CATALOG = (
    ProviderDefinition("ollama", "Ollama", "http://127.0.0.1:11434", True, "ollama", False),
    ProviderDefinition(
        "lm-studio", "LM Studio", "http://127.0.0.1:1234", True, credential_required=False
    ),
    ProviderDefinition(
        "localai", "LocalAI", "http://127.0.0.1:8080", True, credential_required=False
    ),
    ProviderDefinition("vllm", "vLLM", "http://127.0.0.1:8000", True, credential_required=False),
    ProviderDefinition("openrouter", "OpenRouter", "https://openrouter.ai/api", False),
    ProviderDefinition("openai", "OpenAI", "https://api.openai.com", False),
    ProviderDefinition("nvidia-nim", "NVIDIA NIM", "https://integrate.api.nvidia.com", False),
    ProviderDefinition("anthropic", "Anthropic", "https://api.anthropic.com", False, "anthropic"),
    ProviderDefinition(
        "google-gemini",
        "Google Gemini",
        "https://generativelanguage.googleapis.com",
        False,
        "gemini",
    ),
    ProviderDefinition("groq", "Groq", "https://api.groq.com/openai", False),
    ProviderDefinition("mistral", "Mistral AI", "https://api.mistral.ai", False),
    ProviderDefinition("together", "Together AI", "https://api.together.xyz", False),
    ProviderDefinition("custom", "Custom OpenAI-compatible", "", False),
)
PROVIDERS_BY_ID = {item.id: item for item in PROVIDER_CATALOG}


def _is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    return host in {"localhost", "127.0.0.1", "::1"}


def _validate_url(base_url: str, *, consent_remote: bool) -> tuple[str, bool]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("model endpoint must be an absolute HTTP(S) URL")
    remote = not _is_loopback(base_url)
    if remote and not consent_remote:
        raise ValueError("remote model endpoints require explicit --consent-remote")
    if remote and parsed.scheme != "https":
        raise ValueError("remote model endpoints must use HTTPS")
    return base_url.rstrip("/"), remote


def _messages(request: AnalysisRequest, *, retry: bool = False) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": system_prompt(request.report_language),
        },
        {"role": "user", "content": json.dumps(request.context, ensure_ascii=False)},
    ]
    if retry:
        messages.append({"role": "user", "content": "Return only the JSON object, nothing else."})
    return messages


class _BaseAnalysisProvider:
    provider_id: str

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        consent_remote: bool = False,
        timeout_seconds: float = 180,
    ) -> None:
        self.base_url, self.remote = _validate_url(base_url, consent_remote=consent_remote)
        if not model.strip():
            raise ValueError("model must not be empty")
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds

    def _analysis(self, content: str, request: AnalysisRequest) -> AIReportAnalysis:
        try:
            generated = AIAnalysisContent.model_validate(_normalized_analysis_payload(content))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ModelProviderError(
                "ai_output_invalid", "The model returned analysis that did not match the schema."
            ) from error
        self._validate_consistency(generated, request)
        finding_actions = [
            AIFindingAction(
                finding_id=finding_id,
                remediation=action.action,
                verification_steps=[action.expected_effect],
            )
            for action in generated.priority_actions
            for addressed in action.addresses
            for finding_id in request.finding_ids_by_rule.get(addressed, [])
        ]
        return AIReportAnalysis(
            **generated.model_dump(),
            provider=self.provider_id,
            model=self.model,
            remote=self.remote,
            finding_ids=sorted(request.finding_ids),
            finding_actions=finding_actions[:25],
        )

    @staticmethod
    def _validate_consistency(generated: AIAnalysisContent, request: AnalysisRequest) -> None:
        text = generated.ai_analysis.casefold()
        labels = _SEVERITY_LABELS.get(request.report_language, _SEVERITY_LABELS["en"])
        nonzero = [
            (severity, count) for severity, count in request.severity_counts.items() if count > 0
        ]
        for severity, count in nonzero:
            if str(count) not in text or labels[severity] not in text:
                raise ModelProviderError(
                    "ai_output_invalid",
                    "The model analysis did not state the supplied severity distribution.",
                )
        if request.severity_counts.get("medium", 0) > 0 and any(
            phrase in text for phrase in _LOW_ONLY_FRAMING.get(request.report_language, ())
        ):
            raise ModelProviderError(
                "ai_output_invalid",
                "The model analysis contradicted the supplied severity distribution.",
            )
        skipped = [
            item
            for item in request.context.get("coverage", [])
            if isinstance(item, dict) and item.get("status") == "not_evaluated"
        ]
        if skipped and not generated.coverage_caveat:
            raise ModelProviderError(
                "ai_output_invalid",
                "The model analysis omitted the required coverage caveat.",
            )
        caveat = (generated.coverage_caveat or "").casefold()
        missing_areas = [
            str(item.get("area"))
            for item in skipped
            if str(item.get("area")).casefold() not in caveat
        ]
        if missing_areas:
            raise ModelProviderError(
                "ai_output_invalid",
                "The model analysis did not name every unevaluated coverage area.",
            )

    async def _analysis_with_retry(
        self,
        content: str,
        request: AnalysisRequest,
        retry: Callable[[], Awaitable[str]],
    ) -> AIReportAnalysis:
        try:
            return self._analysis(content, request)
        except ModelProviderError as error:
            if error.code != "ai_output_invalid":
                raise
        return self._analysis(await retry(), request)

    async def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method, f"{self.base_url}{path}", json=payload, headers=headers
                )
                response.raise_for_status()
                if len(response.content) > 256_000:
                    raise ModelProviderError(
                        "ai_response_too_large",
                        "The model response exceeded the 256 KiB safety limit.",
                    )
                value = response.json()
        except httpx.TimeoutException as error:
            raise ModelProviderError(
                "ai_provider_timeout",
                f"The AI provider did not respond within {self.timeout_seconds:g} seconds.",
            ) from error
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise ModelProviderError(
                f"ai_provider_http_{status}",
                f"The AI provider rejected the request with HTTP {status}.",
            ) from error
        except httpx.RequestError as error:
            raise ModelProviderError(
                "ai_provider_unreachable", "The AI provider could not be reached."
            ) from error
        except ValueError as error:
            raise ModelProviderError(
                "ai_response_not_json", "The AI provider response was not valid JSON."
            ) from error
        if not isinstance(value, dict):
            raise ModelProviderError(
                "ai_response_invalid", "The AI provider response had an invalid shape."
            )
        return value

    async def _post(
        self,
        path: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, payload, headers)

    async def _post_with_http_400_fallback(
        self,
        path: str,
        payload: Mapping[str, object],
        fallback_payload: Mapping[str, object],
        *,
        terminal_message: str,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Retry once when a compatible server rejects an optional request field."""

        try:
            return await self._post(path, payload, headers)
        except ModelProviderError as error:
            if error.code != "ai_provider_http_400":
                raise
        try:
            return await self._post(path, fallback_payload, headers)
        except ModelProviderError as error:
            if error.code != "ai_provider_http_400":
                raise
            raise ModelProviderError("ai_provider_request_invalid", terminal_message) from error


def _normalized_analysis_payload(content: str) -> dict[str, Any]:
    """Strip one optional JSON fence and parse exactly one JSON object."""

    text = content.strip().removeprefix("\ufeff").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise TypeError("analysis payload must be an object")
    return value


_SEVERITY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "info",
    },
    "tr": {
        "critical": "kritik",
        "high": "yüksek",
        "medium": "orta",
        "low": "düşük",
        "info": "bilgi",
    },
    "de": {
        "critical": "kritisch",
        "high": "hoch",
        "medium": "mittel",
        "low": "niedrig",
        "info": "info",
    },
    "fr": {
        "critical": "critique",
        "high": "élevé",
        "medium": "moyen",
        "low": "faible",
        "info": "info",
    },
    "zh-CN": {
        "critical": "严重",
        "high": "高",
        "medium": "中",
        "low": "低",
        "info": "信息",
    },
    "it": {
        "critical": "critico",
        "high": "alto",
        "medium": "medio",
        "low": "basso",
        "info": "informativo",
    },
}
_LOW_ONLY_FRAMING: dict[str, tuple[str, ...]] = {
    "en": ("low-level", "minor findings", "minor issues"),
    "tr": ("düşük seviyeli", "önemsiz bulgu", "küçük sorun"),
    "de": ("geringfügige befunde",),
    "fr": ("constats mineurs",),
    "zh-CN": ("仅低风险",),
    "it": ("risultati minori",),
}


class OllamaAnalysisProvider(_BaseAnalysisProvider):
    provider_id = "ollama"

    async def analyze(self, request: AnalysisRequest) -> AIReportAnalysis:
        async def chat(*, retry: bool) -> str:
            payload: dict[str, object] = {
                "model": self.model,
                "messages": _messages(request, retry=retry),
                "stream": False,
                "format": ("json" if retry else AIAnalysisContent.model_json_schema()),
                "options": {"temperature": 0.1},
            }
            value = await self._post_with_http_400_fallback(
                "/api/chat",
                payload,
                {**payload, "format": "json"},
                terminal_message=(
                    "Ollama rejected both schema and JSON compatibility requests. Verify that the "
                    "selected model is installed and that the endpoint supports /api/chat."
                ),
            )
            content = (
                value.get("message", {}).get("content")
                if isinstance(value.get("message"), dict)
                else None
            )
            if not isinstance(content, str):
                raise ModelProviderError(
                    "ai_response_missing_content",
                    "The Ollama response did not contain analysis text.",
                )
            return content

        content = await chat(retry=False)
        return await self._analysis_with_retry(content, request, lambda: chat(retry=True))

    async def list_models(self) -> list[str]:
        value = await self._request("GET", "/api/tags")
        models = value.get("models")
        if not isinstance(models, list):
            raise ModelProviderError(
                "ai_model_inventory_invalid", "Ollama returned an invalid model inventory."
            )
        return sorted(
            item["name"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )[:200]


class OpenAICompatibleAnalysisProvider(_BaseAnalysisProvider):
    provider_id = "openai-compatible"

    def __init__(
        self, *, api_key: str = "", provider_id: str = "openai-compatible", **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.api_key = api_key
        self.provider_id = provider_id

    async def analyze(self, request: AnalysisRequest) -> AIReportAnalysis:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

        async def chat(*, retry: bool) -> str:
            payload: dict[str, object] = {
                "model": self.model,
                "messages": _messages(request, retry=retry),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            value = await self._post_with_http_400_fallback(
                "/v1/chat/completions",
                payload,
                {key: value for key, value in payload.items() if key != "response_format"},
                headers=headers,
                terminal_message=(
                    "The provider rejected both structured and compatibility requests. Verify that "
                    "the selected model exists and the endpoint supports chat completions."
                ),
            )
            choices = value.get("choices")
            content = (
                choices[0].get("message", {}).get("content")
                if isinstance(choices, list) and choices and isinstance(choices[0], dict)
                else None
            )
            if not isinstance(content, str):
                raise ModelProviderError(
                    "ai_response_missing_content",
                    "The OpenAI-compatible response did not contain analysis text.",
                )
            return content

        content = await chat(retry=False)
        return await self._analysis_with_retry(content, request, lambda: chat(retry=True))

    async def list_models(self) -> list[str]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        value = await self._request("GET", "/v1/models", headers=headers)
        models = value.get("data")
        if not isinstance(models, list):
            raise ModelProviderError(
                "ai_model_inventory_invalid", "The provider returned an invalid model inventory."
            )
        return sorted(
            item["id"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )[:200]


class AnthropicAnalysisProvider(_BaseAnalysisProvider):
    provider_id = "anthropic"

    def __init__(self, *, api_key: str, **kwargs: object) -> None:
        if not api_key.strip():
            raise ValueError("API key is unavailable")
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.api_key = api_key

    async def analyze(self, request: AnalysisRequest) -> AIReportAnalysis:

        async def chat(*, retry: bool) -> str:
            messages = _messages(request, retry=retry)
            value = await self._post(
                "/v1/messages",
                {
                    "model": self.model,
                    "max_tokens": 2500,
                    "temperature": 0.1,
                    "system": messages[0]["content"],
                    "messages": messages[1:],
                },
                {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            )
            blocks = value.get("content")
            content = blocks[0].get("text") if isinstance(blocks, list) and blocks else None
            if not isinstance(content, str):
                raise ModelProviderError(
                    "ai_response_missing_content",
                    "The Anthropic response did not contain analysis text.",
                )
            return content

        content = await chat(retry=False)
        return await self._analysis_with_retry(content, request, lambda: chat(retry=True))

    async def list_models(self) -> list[str]:
        value = await self._request(
            "GET",
            "/v1/models",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        models = value.get("data")
        if not isinstance(models, list):
            raise ModelProviderError(
                "ai_model_inventory_invalid", "Anthropic returned an invalid model inventory."
            )
        return sorted(
            item["id"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )[:200]


class GeminiAnalysisProvider(_BaseAnalysisProvider):
    provider_id = "google-gemini"

    def __init__(self, *, api_key: str, **kwargs: object) -> None:
        if not api_key.strip():
            raise ValueError("API key is unavailable")
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.api_key = api_key

    async def analyze(self, request: AnalysisRequest) -> AIReportAnalysis:

        async def chat(*, retry: bool) -> str:
            messages = _messages(request, retry=retry)
            user_content = "\n\n".join(message["content"] for message in messages[1:])
            value = await self._post(
                f"/v1beta/models/{self.model}:generateContent",
                {
                    "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
                    "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                        "responseSchema": AIAnalysisContent.model_json_schema(),
                    },
                },
                {"x-goog-api-key": self.api_key},
            )
            candidates = value.get("candidates")
            content = None
            if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
                candidate_content = candidates[0].get("content")
                if isinstance(candidate_content, dict):
                    parts = candidate_content.get("parts")
                    if isinstance(parts, list) and parts and isinstance(parts[0], dict):
                        content = parts[0].get("text")
            if not isinstance(content, str):
                raise ModelProviderError(
                    "ai_response_missing_content",
                    "The Gemini response did not contain analysis text.",
                )
            return content

        content = await chat(retry=False)
        return await self._analysis_with_retry(content, request, lambda: chat(retry=True))

    async def list_models(self) -> list[str]:
        value = await self._request(
            "GET", "/v1beta/models", headers={"x-goog-api-key": self.api_key}
        )
        models = value.get("models")
        if not isinstance(models, list):
            raise ModelProviderError(
                "ai_model_inventory_invalid", "Gemini returned an invalid model inventory."
            )
        return sorted(
            item["name"].removeprefix("models/")
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )[:200]


def create_analysis_provider(
    config: AIProviderConfig,
    *,
    secret_resolver: Callable[[str], str],
) -> (
    OllamaAnalysisProvider
    | OpenAICompatibleAnalysisProvider
    | AnthropicAnalysisProvider
    | GeminiAnalysisProvider
):
    """Compose a provider from a validated, non-secret scan configuration."""

    validated = AIProviderConfig.model_validate(config)
    if not validated.enabled or validated.provider is None or validated.model is None:
        raise ValueError("AI provider is not enabled")
    definition = PROVIDERS_BY_ID[validated.provider]
    base_url = (validated.base_url or definition.default_base_url).strip()
    if not base_url:
        raise ValueError("custom AI providers require a base URL")
    common: dict[str, object] = {
        "base_url": base_url,
        "model": validated.model,
        "consent_remote": validated.remote_consent,
        "timeout_seconds": validated.timeout_seconds,
    }
    api_key = secret_resolver(validated.credential_ref) if validated.credential_ref else ""
    if definition.protocol == "ollama":
        return OllamaAnalysisProvider(**common)  # type: ignore[arg-type]
    if definition.protocol == "anthropic":
        return AnthropicAnalysisProvider(api_key=api_key, **common)
    if definition.protocol == "gemini":
        return GeminiAnalysisProvider(api_key=api_key, **common)
    return OpenAICompatibleAnalysisProvider(api_key=api_key, provider_id=definition.id, **common)


async def discover_provider_models(
    config: AIProviderConfig, *, secret_resolver: Callable[[str], str]
) -> list[str]:
    """List bounded provider model metadata without sending report content."""

    provider = create_analysis_provider(config, secret_resolver=secret_resolver)
    return await provider.list_models()
