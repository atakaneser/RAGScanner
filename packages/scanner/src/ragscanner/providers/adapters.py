"""Consent-aware HTTP adapters for optional report enrichment."""

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from ragscanner.ai_analysis.models import (
    AIAnalysisContent,
    AIFindingAction,
    AIProviderConfig,
    AIReportAnalysis,
)
from ragscanner.ai_analysis.prompt import retry_system_prompt, system_prompt
from ragscanner.ai_analysis.service import AnalysisRequest

MAX_RETRY_CONTEXT_CHARACTERS = 6_500
_MINIMAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {"ai_analysis": {"type": "string"}},
    "required": ["ai_analysis"],
}


class ModelProviderError(RuntimeError):
    """A safe, user-facing provider failure."""

    def __init__(self, code: str, message: str, *, detail_code: str | None = None) -> None:
        self.code = code
        self.safe_message = message
        self.detail_code = detail_code
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


def _provider_text(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _retry_context(request: AnalysisRequest) -> dict[str, Any]:
    """Reduce recovery input so the schema instruction stays inside small model windows."""

    source = request.context.get("meta", {})
    meta = source if isinstance(source, dict) else {}
    selection = request.context.get("selection", {})
    compact: dict[str, Any] = {
        "source": _provider_text(meta.get("source"), 180),
        "scores": request.context.get("scores", {}),
        "severity_counts": request.severity_counts,
        "selection": selection if isinstance(selection, dict) else {},
        "not_evaluated": [
            _provider_text(item.get("area"), 120)
            for item in request.context.get("coverage", [])
            if isinstance(item, dict) and item.get("status") == "not_evaluated"
        ],
        "findings": [],
    }
    findings = request.context.get("findings", [])
    if not isinstance(findings, list):
        return compact
    for supplied in findings[:8]:
        if not isinstance(supplied, dict):
            continue
        evidence = supplied.get("evidence", [])
        locations = [
            {
                "file": _provider_text(item.get("file"), 180),
                "page": item.get("page"),
                "lines": _provider_text(item.get("lines"), 40),
            }
            for item in evidence[:2]
            if isinstance(item, dict)
        ]
        item = {
            "rule_id": _provider_text(supplied.get("rule_id"), 120),
            "title": _provider_text(supplied.get("title"), 160),
            "severity": _provider_text(supplied.get("severity"), 20),
            "affected_chunks": supplied.get("affected_chunks"),
            "recommendation": _provider_text(supplied.get("recommendation"), 280),
            "locations": locations,
        }
        candidate = {**compact, "findings": [*compact["findings"], item]}
        if (
            len(json.dumps(candidate, ensure_ascii=False, separators=(",", ":")))
            > MAX_RETRY_CONTEXT_CHARACTERS
        ):
            break
        compact["findings"].append(item)
    return compact


def _messages(request: AnalysisRequest, *, retry: bool = False) -> list[dict[str, str]]:
    if retry:
        return [
            {
                "role": "system",
                "content": retry_system_prompt(request.report_language),
            },
            {
                "role": "user",
                "content": json.dumps(
                    _retry_context(request),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ]
    messages = [
        {
            "role": "system",
            "content": system_prompt(request.report_language),
        },
        {
            "role": "user",
            "content": json.dumps(
                request.context,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
    ]
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
            payload = _normalized_analysis_payload(content)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ModelProviderError(
                "ai_output_invalid",
                "The model did not return one valid JSON object.",
                detail_code="invalid_json",
            ) from error
        try:
            generated = AIAnalysisContent.model_validate(
                _compatible_analysis_payload(payload, request.report_language)
            )
        except ValidationError as error:
            raise ModelProviderError(
                "ai_output_invalid",
                "The model JSON omitted required analysis content.",
                detail_code="schema_mismatch",
            ) from error
        generated = self._apply_deterministic_guards(generated, request)
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
            finding_ids=sorted(request.finding_ids)[:25],
            finding_actions=finding_actions[:25],
        )

    @staticmethod
    def _apply_deterministic_guards(
        generated: AIAnalysisContent, request: AnalysisRequest
    ) -> AIAnalysisContent:
        text = generated.ai_analysis.casefold()
        labels = _SEVERITY_LABELS.get(request.report_language, _SEVERITY_LABELS["en"])
        nonzero = [
            (severity, count) for severity, count in request.severity_counts.items() if count > 0
        ]
        distribution_missing = any(
            str(count) not in text or labels[severity] not in text for severity, count in nonzero
        )
        if request.severity_counts.get("medium", 0) > 0 and any(
            phrase in text for phrase in _LOW_ONLY_FRAMING.get(request.report_language, ())
        ):
            raise ModelProviderError(
                "ai_output_invalid",
                "The model analysis contradicted the supplied severity distribution.",
                detail_code="severity_contradiction",
            )
        analysis = generated.ai_analysis
        if distribution_missing and nonzero:
            analysis = f"{_severity_distribution(request)} {analysis}"
        skipped = [
            item
            for item in request.context.get("coverage", [])
            if isinstance(item, dict) and item.get("status") == "not_evaluated"
        ]
        caveat = (generated.coverage_caveat or "").casefold()
        missing_areas = [
            str(item.get("area"))
            for item in skipped
            if str(item.get("area")).casefold() not in caveat
        ]
        coverage_caveat = generated.coverage_caveat
        if missing_areas:
            deterministic_caveat = _coverage_caveat(missing_areas, request.report_language)
            coverage_caveat = (
                f"{coverage_caveat.rstrip()} {deterministic_caveat}"
                if coverage_caveat
                else deterministic_caveat
            )
        selection = request.context.get("selection", {})
        omitted_groups = (
            int(selection.get("omitted_finding_groups", 0)) if isinstance(selection, dict) else 0
        )
        if omitted_groups > 0:
            deterministic_caveat = _selection_caveat(
                omitted_groups,
                int(selection.get("total_finding_groups", omitted_groups)),
                request.report_language,
            )
            coverage_caveat = (
                f"{coverage_caveat.rstrip()} {deterministic_caveat}"
                if coverage_caveat
                else deterministic_caveat
            )
        return generated.model_copy(
            update={
                "ai_analysis": analysis[:2_000],
                "coverage_caveat": (
                    coverage_caveat[:1_500] if coverage_caveat is not None else None
                ),
            }
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
    """Extract one bounded analysis object from common local-model wrappers."""

    text = content.strip().removeprefix("\ufeff").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = _embedded_analysis_object(text)
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, dict) or not _looks_like_analysis_object(value):
        raise TypeError("analysis payload must be an analysis object")
    return value


_ANALYSIS_ROOT_KEYS = {
    "ai_analysis",
    "executive_summary",
    "summary",
    "analysis",
    "result",
    "output",
    "response",
    "content",
    "report",
}


def _looks_like_analysis_object(value: dict[str, Any]) -> bool:
    return any(key in value for key in _ANALYSIS_ROOT_KEYS)


def _embedded_analysis_object(text: str) -> dict[str, Any]:
    """Find the first expected JSON object without repairing ambiguous JSON syntax."""

    decoder = json.JSONDecoder()
    candidates = 0
    for index, character in enumerate(text):
        if character != "{":
            continue
        candidates += 1
        if candidates > 64:
            break
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and _looks_like_analysis_object(value):
            return value
    raise json.JSONDecodeError("no analysis object found", text, 0)


def _text(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized[:limit] if normalized else None


def _text_list(value: object, *, limit: int, item_limit: int) -> list[str]:
    supplied = [value] if isinstance(value, str) else value
    if not isinstance(supplied, list):
        return []
    return [text for item in supplied[:limit] if (text := _text(item, item_limit)) is not None]


def _enum(
    value: object,
    *,
    allowed: set[str],
    aliases: Mapping[str, str],
    fallback: str,
) -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in allowed else fallback


def _compatible_analysis_payload(payload: dict[str, Any], report_language: str) -> dict[str, Any]:
    """Repair bounded, unambiguous local-model shape variations before validation."""

    for wrapper in ("analysis", "result", "output"):
        nested = payload.get(wrapper)
        if isinstance(nested, dict) and any(
            key in nested for key in ("ai_analysis", "executive_summary", "summary")
        ):
            payload = nested
            break

    analysis = _text(
        payload.get("ai_analysis")
        or payload.get("executive_summary")
        or payload.get("summary")
        or payload.get("analysis")
        or payload.get("response")
        or payload.get("content")
        or payload.get("report"),
        2_000,
    )
    score_commentary = _text(payload.get("score_commentary"), 2_000) or analysis

    root_causes: list[dict[str, object]] = []
    raw_root_causes = payload.get("root_causes")
    if isinstance(raw_root_causes, dict):
        raw_root_causes = [raw_root_causes]
    if isinstance(raw_root_causes, list):
        for item in raw_root_causes[:8]:
            if not isinstance(item, dict):
                continue
            finding_rules = _text_list(
                item.get("finding_rules") or item.get("rules"),
                limit=20,
                item_limit=240,
            )
            example_files = _text_list(
                item.get("example_files") or item.get("files"),
                limit=20,
                item_limit=500,
            )
            label = _text(item.get("label") or item.get("name"), 240)
            explanation = _text(
                item.get("explanation") or item.get("description"),
                1_500,
            )
            if not finding_rules or not example_files or not label or not explanation:
                continue
            root_causes.append(
                {
                    "pattern": _enum(
                        item.get("pattern"),
                        allowed={"P1", "P2", "P3", "P4", "other"},
                        aliases={
                            "p1": "P1",
                            "p2": "P2",
                            "p3": "P3",
                            "p4": "P4",
                            "boilerplate_duplication": "P1",
                            "self_duplication": "P2",
                            "template_corpus": "P3",
                            "version_variants": "P4",
                            "diğer": "other",
                        },
                        fallback="other",
                    ),
                    "label": label,
                    "finding_rules": finding_rules,
                    "example_files": example_files,
                    "explanation": explanation,
                    "confidence": _enum(
                        item.get("confidence"),
                        allowed={"confirmed", "likely"},
                        aliases={
                            "kesin": "confirmed",
                            "doğrulandı": "confirmed",
                            "muhtemel": "likely",
                            "olası": "likely",
                        },
                        fallback="likely",
                    ),
                }
            )

    action_default = _ACTION_EFFECT_DEFAULTS.get(report_language, _ACTION_EFFECT_DEFAULTS["en"])
    priority_actions: list[dict[str, object]] = []
    raw_actions = payload.get("priority_actions")
    if isinstance(raw_actions, (dict, str)):
        raw_actions = [raw_actions]
    if isinstance(raw_actions, list):
        for index, item in enumerate(raw_actions[:8], start=1):
            supplied = {"action": item} if isinstance(item, str) else item
            if not isinstance(supplied, dict):
                continue
            action = _text(
                supplied.get("action") or supplied.get("recommendation"),
                1_500,
            )
            if not action:
                continue
            priority_actions.append(
                {
                    "order": (
                        supplied["order"]
                        if isinstance(supplied.get("order"), int) and 1 <= supplied["order"] <= 20
                        else index
                    ),
                    "action": action,
                    "target": _enum(
                        supplied.get("target"),
                        allowed={"ingestion", "chunking", "corpus", "configuration"},
                        aliases={
                            "indexing": "ingestion",
                            "index": "ingestion",
                            "pipeline": "ingestion",
                            "data_ingestion": "ingestion",
                            "indeksleme": "ingestion",
                            "veri_alımı": "ingestion",
                            "parçalama": "chunking",
                            "yapılandırma": "configuration",
                        },
                        fallback="configuration",
                    ),
                    "addresses": _text_list(
                        supplied.get("addresses"),
                        limit=20,
                        item_limit=240,
                    ),
                    "expected_effect": (
                        _text(supplied.get("expected_effect"), 1_500) or action_default
                    ),
                    "effort": _enum(
                        supplied.get("effort"),
                        allowed={"low", "medium", "high"},
                        aliases={
                            "düşük": "low",
                            "orta": "medium",
                            "yüksek": "high",
                        },
                        fallback="medium",
                    ),
                }
            )

    question_default = _QUESTION_INFORMS_DEFAULTS.get(
        report_language, _QUESTION_INFORMS_DEFAULTS["en"]
    )
    review_questions: list[dict[str, str]] = []
    raw_questions = payload.get("review_questions")
    if isinstance(raw_questions, (dict, str)):
        raw_questions = [raw_questions]
    if isinstance(raw_questions, list):
        for item in raw_questions[:8]:
            supplied = {"question": item} if isinstance(item, str) else item
            if not isinstance(supplied, dict):
                continue
            question = _text(supplied.get("question"), 1_000)
            if question:
                review_questions.append(
                    {
                        "question": question,
                        "informs": (_text(supplied.get("informs"), 1_000) or question_default),
                    }
                )

    return {
        "ai_analysis": analysis,
        "root_causes": root_causes,
        "priority_actions": priority_actions,
        "review_questions": review_questions,
        "score_commentary": score_commentary,
        "coverage_caveat": _text(payload.get("coverage_caveat"), 1_500),
    }


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

_SEVERITY_DISTRIBUTION_TEMPLATES = {
    "en": "Severity distribution: {items}.",
    "tr": "Önem dağılımı: {items}.",
    "de": "Schweregradverteilung: {items}.",
    "fr": "Répartition des sévérités : {items}.",
    "zh-CN": "严重性分布：{items}。",
    "it": "Distribuzione della gravità: {items}.",
}

_COVERAGE_CAVEAT_TEMPLATES = {
    "en": "Scores cover evaluated areas only; not evaluated: {areas}.",
    "tr": "Puanlar yalnızca değerlendirilen alanları kapsar; değerlendirilmeyenler: {areas}.",
    "de": "Die Bewertungen decken nur geprüfte Bereiche ab; nicht bewertet: {areas}.",
    "fr": "Les scores couvrent uniquement les domaines évalués ; non évalués : {areas}.",
    "zh-CN": "分数仅涵盖已评估领域；未评估：{areas}。",
    "it": "I punteggi coprono solo le aree valutate; non valutate: {areas}.",
}

_SELECTION_CAVEAT_TEMPLATES = {
    "en": (
        "The advisory analysis prioritizes the supplied groups; {omitted} of {total} finding groups "
        "remain in the exhaustive deterministic report."
    ),
    "tr": (
        "Danışman analiz sağlanan grupları önceliklendirir; {total} bulgu grubunun {omitted} tanesi "
        "eksiksiz deterministik raporda kalır."
    ),
    "de": (
        "Die beratende Analyse priorisiert die gelieferten Gruppen; {omitted} von {total} "
        "Befundgruppen verbleiben im vollständigen deterministischen Bericht."
    ),
    "fr": (
        "L’analyse consultative priorise les groupes fournis ; {omitted} groupes sur {total} "
        "restent dans le rapport déterministe exhaustif."
    ),
    "zh-CN": "建议分析优先处理所提供的组；{total} 个发现组中仍有 {omitted} 个保留在完整的确定性报告中。",
    "it": (
        "L’analisi consultiva dà priorità ai gruppi forniti; {omitted} gruppi su {total} restano "
        "nel rapporto deterministico completo."
    ),
}

_ACTION_EFFECT_DEFAULTS = {
    "en": "Re-run the deterministic scan to verify the effect.",
    "tr": "Etkisini doğrulamak için deterministik taramayı yeniden çalıştırın.",
    "de": "Führen Sie den deterministischen Scan erneut aus, um die Wirkung zu prüfen.",
    "fr": "Relancez l’analyse déterministe pour vérifier l’effet.",
    "zh-CN": "重新运行确定性扫描以验证效果。",
    "it": "Esegui nuovamente la scansione deterministica per verificare l’effetto.",
}

_QUESTION_INFORMS_DEFAULTS = {
    "en": "The related remediation decision.",
    "tr": "İlgili düzeltme kararı.",
    "de": "Die zugehörige Behebungsentscheidung.",
    "fr": "La décision de correction associée.",
    "zh-CN": "相关修复决策。",
    "it": "La relativa decisione di correzione.",
}


def _severity_distribution(request: AnalysisRequest) -> str:
    labels = _SEVERITY_LABELS.get(request.report_language, _SEVERITY_LABELS["en"])
    values = [
        f"{count} {labels[severity]}"
        for severity, count in request.severity_counts.items()
        if count > 0
    ]
    template = _SEVERITY_DISTRIBUTION_TEMPLATES.get(
        request.report_language, _SEVERITY_DISTRIBUTION_TEMPLATES["en"]
    )
    return template.format(items=", ".join(values))


def _coverage_caveat(areas: list[str], report_language: str) -> str:
    template = _COVERAGE_CAVEAT_TEMPLATES.get(report_language, _COVERAGE_CAVEAT_TEMPLATES["en"])
    return template.format(areas=", ".join(areas))


def _selection_caveat(omitted: int, total: int, report_language: str) -> str:
    template = _SELECTION_CAVEAT_TEMPLATES.get(report_language, _SELECTION_CAVEAT_TEMPLATES["en"])
    return template.format(omitted=omitted, total=total)


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
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 16_384,
                    "num_predict": 768 if retry else 2_048,
                },
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
                        "responseSchema": (
                            _MINIMAL_ANALYSIS_SCHEMA
                            if retry
                            else AIAnalysisContent.model_json_schema()
                        ),
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
