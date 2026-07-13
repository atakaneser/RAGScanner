"""Pure parsing, validation, filtering, and rendering for active test definitions."""

import json
import re
from collections.abc import Iterable, Mapping

from pydantic import BaseModel, Field, field_validator, model_validator

from ragscanner.domain.active import PayloadVariant, SecurityTestCase
from ragscanner.domain.enums import SafetyMode, SideEffectRisk
from ragscanner.domain.helpers import contains_unreferenced_secret

ACTIVE_PACK_SCHEMA_VERSION = "1.0.0"
SAFE_PLACEHOLDERS = frozenset(
    {
        "CANARY_TOKEN",
        "TEST_SESSION_ID",
        "SAFE_TOOL_NAME",
        "FAKE_DOCUMENT_NAME",
        "AUTHORIZED_TEST_USER",
        "TARGET_NAME",
    }
)
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_EXTERNAL_TARGET = re.compile(r"(?i)\b(?:https?|ftp)://")
_DESTRUCTIVE = (
    re.compile(r"(?i)\brm\s+-rf\b"),
    re.compile(r"(?i)\b(?:drop\s+(?:database|table)|truncate\s+table|delete\s+from)\b"),
    re.compile(r"(?i)\b(?:shutdown|reboot|format\s+[a-z]:)\b"),
)
_PACK_FIELDS = {"schema_version", "pack_id", "version", "description", "test_cases"}
_CASE_FIELDS = {
    "id",
    "name",
    "category",
    "description",
    "severity",
    "detection_type",
    "default_safety_mode",
    "side_effect_risk",
    "requires_tool_access",
    "requires_retrieval",
    "languages",
    "tags",
    "payloads",
    "control_payload",
    "expected_safe_behavior",
    "unsafe_indicators",
    "safe_indicators",
    "ambiguous_indicators",
    "remediation",
    "references",
    "enabled",
    "version",
    "metadata",
}
_PAYLOAD_FIELDS = {
    "id",
    "content",
    "language",
    "encoding",
    "tags",
    "safe_for_production",
    "expected_behavior",
    "placeholders",
    "metadata",
}


def _validate_semver(value: str) -> str:
    if not _SEMVER.fullmatch(value):
        raise ValueError("version must use MAJOR.MINOR.PATCH")
    return value


def _require_fields(value: object, required: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    missing = required - set(value)
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(sorted(missing))}")
    return value


def _validate_raw_schema(raw: object) -> None:
    pack = _require_fields(raw, _PACK_FIELDS, "rule pack")
    cases = pack["test_cases"]
    if not isinstance(cases, list):
        raise ValueError("test_cases must be a JSON array")
    for case_value in cases:
        case = _require_fields(case_value, _CASE_FIELDS, "test case")
        payloads = case["payloads"]
        if not isinstance(payloads, list):
            raise ValueError("payloads must be a JSON array")
        for payload in payloads:
            _require_fields(payload, _PAYLOAD_FIELDS, "payload")
        control = case["control_payload"]
        if control is not None:
            _require_fields(control, _PAYLOAD_FIELDS, "control payload")


def _validate_payload(payload: PayloadVariant) -> None:
    found = set(_PLACEHOLDER.findall(payload.content))
    declared = set(payload.placeholders)
    unknown = (found | declared) - SAFE_PLACEHOLDERS
    if unknown:
        raise ValueError(f"unknown placeholders: {', '.join(sorted(unknown))}")
    if found != declared:
        raise ValueError("payload placeholders must exactly match content placeholders")
    if len(payload.placeholders) != len(declared):
        raise ValueError("duplicate placeholder declaration")
    if contains_unreferenced_secret(payload.content) or contains_unreferenced_secret(
        payload.metadata
    ):
        raise ValueError("payload contains a raw or real-looking credential")
    if _EMAIL.search(payload.content):
        raise ValueError("payload contains a real-looking email address")
    if _EXTERNAL_TARGET.search(payload.content):
        raise ValueError("payload contains a real external target")
    if any(pattern.search(payload.content) for pattern in _DESTRUCTIVE):
        raise ValueError("payload contains a destructive command or SQL statement")
    unsafe_marked = "unsafe" in {tag.casefold() for tag in payload.tags} or bool(
        payload.metadata.get("unsafe")
    )
    if unsafe_marked and payload.safe_for_production:
        raise ValueError("unsafe payload cannot be marked safe_for_production")


class ActiveRulePack(BaseModel):
    schema_version: str
    pack_id: str = Field(min_length=1)
    version: str
    description: str = Field(min_length=1)
    test_cases: list[SecurityTestCase] = Field(min_length=1)

    _schema_semver = field_validator("schema_version")(_validate_semver)
    _pack_semver = field_validator("version")(_validate_semver)

    @model_validator(mode="after")
    def validate_cases(self) -> "ActiveRulePack":
        if self.schema_version != ACTIVE_PACK_SCHEMA_VERSION:
            raise ValueError("unsupported active rule-pack schema version")
        case_ids: set[str] = set()
        payload_ids: set[str] = set()
        for case in self.test_cases:
            _validate_semver(case.version)
            if case.id in case_ids:
                raise ValueError(f"duplicate test-case ID: {case.id}")
            case_ids.add(case.id)
            local_ids = [payload.id for payload in case.payloads]
            if case.control_payload is not None:
                local_ids.append(case.control_payload.id)
            if len(local_ids) != len(set(local_ids)):
                raise ValueError(f"duplicate payload ID in test case: {case.id}")
            for payload in [
                *case.payloads,
                *([case.control_payload] if case.control_payload else []),
            ]:
                _validate_payload(payload)
                if payload.id in payload_ids:
                    raise ValueError(f"duplicate payload ID: {payload.id}")
                payload_ids.add(payload.id)
            if case.default_safety_mode is SafetyMode.SAFE:
                if case.side_effect_risk is SideEffectRisk.DESTRUCTIVE:
                    raise ValueError("destructive test case cannot default to safe mode")
                if any(not payload.safe_for_production for payload in case.payloads):
                    raise ValueError("safe-mode test case contains a production-unsafe payload")
            if case.severity.value in {"high", "critical"} and case.control_payload is None:
                raise ValueError("high and critical test cases require a control payload")
        return self


class ActiveTestLibrary:
    """Immutable-style deterministic view over validated test-case definitions."""

    def __init__(self, cases: Iterable[SecurityTestCase]) -> None:
        ordered = sorted((case.model_copy(deep=True) for case in cases), key=lambda case: case.id)
        ids = [case.id for case in ordered]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate test-case ID across rule packs")
        payload_ids = [
            payload.id
            for case in ordered
            for payload in [
                *case.payloads,
                *([case.control_payload] if case.control_payload else []),
            ]
        ]
        if len(payload_ids) != len(set(payload_ids)):
            raise ValueError("duplicate payload ID across rule packs")
        self._cases = tuple(ordered)

    @classmethod
    def from_texts(cls, texts: Iterable[str | bytes]) -> "ActiveTestLibrary":
        cases: list[SecurityTestCase] = []
        for text in texts:
            try:
                raw = json.loads(text)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("invalid active rule-pack JSON") from error
            _validate_raw_schema(raw)
            pack = ActiveRulePack.model_validate(raw)
            cases.extend(pack.test_cases)
        return cls(cases)

    def select(
        self,
        *,
        categories: set[str] | None = None,
        tags: set[str] | None = None,
        languages: set[str] | None = None,
        enabled: bool | None = True,
        safety_mode: SafetyMode | None = None,
    ) -> list[SecurityTestCase]:
        normalized_tags = {tag.casefold() for tag in tags or set()}
        normalized_languages = {language.casefold() for language in languages or set()}
        selected = []
        for case in self._cases:
            if categories and case.category not in categories:
                continue
            if normalized_tags and not normalized_tags.intersection(
                tag.casefold() for tag in case.tags
            ):
                continue
            if normalized_languages and not normalized_languages.intersection(
                language.casefold() for language in case.languages
            ):
                continue
            if enabled is not None and case.enabled is not enabled:
                continue
            if safety_mode is SafetyMode.SAFE and (
                case.default_safety_mode is not SafetyMode.SAFE
                or any(not payload.safe_for_production for payload in case.payloads)
            ):
                continue
            selected.append(case.model_copy(deep=True))
        return selected


def render_payload(payload: PayloadVariant, values: Mapping[str, str]) -> PayloadVariant:
    """Render only declared safe placeholders using literal replacement."""

    _validate_payload(payload)
    supplied = set(values)
    declared = set(payload.placeholders)
    if supplied != declared:
        missing = declared - supplied
        extra = supplied - declared
        raise ValueError(
            f"placeholder values mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    content = payload.content
    for name in sorted(declared):
        value = values[name]
        if not value or "{{" in value or "}}" in value:
            raise ValueError("placeholder values must be non-empty literal strings")
        content = content.replace(f"{{{{{name}}}}}", value)
    rendered = payload.model_copy(update={"content": content, "placeholders": []}, deep=True)
    _validate_payload(rendered)
    return rendered
