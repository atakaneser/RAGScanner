"""Validation tests for versioned active security rule packs."""

import base64
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from ragscanner.domain import SafetyMode
from ragscanner.security import ActiveTestLibrary, render_payload
from ragscanner.security.file_adapter import load_active_rule_pack_files

RULE_DIR = Path("rules/active")


def rule_paths() -> list[Path]:
    return sorted(RULE_DIR.glob("*.json"))


def raw_pack(name: str = "prompt_injection.json") -> dict[str, Any]:
    return json.loads((RULE_DIR / name).read_text(encoding="utf-8"))


def parse_raw(*packs: dict[str, Any]) -> ActiveTestLibrary:
    return ActiveTestLibrary.from_texts(json.dumps(pack) for pack in packs)


def test_successfully_loads_all_versioned_rule_packs() -> None:
    library = load_active_rule_pack_files(rule_paths())
    cases = library.select()
    assert len(cases) == 8
    assert all(case.version == "1.0.0" for case in cases)
    assert {case.category for case in cases} == {
        "prompt_injection",
        "system_prompt_extraction",
        "data_leakage",
        "retrieval_exposure",
        "tool_abuse",
        "context_manipulation",
        "citation_manipulation",
        "encoded_payloads",
    }


def test_invalid_json_schema_and_version_are_rejected() -> None:
    with pytest.raises(ValueError, match="invalid active rule-pack JSON"):
        ActiveTestLibrary.from_texts(["not-json"])
    pack = raw_pack()
    pack["schema_version"] = "2.0.0"
    with pytest.raises(ValidationError, match="unsupported"):
        parse_raw(pack)
    pack = raw_pack()
    pack["version"] = "version-one"
    with pytest.raises(ValidationError, match=r"MAJOR\.MINOR\.PATCH"):
        parse_raw(pack)
    pack = raw_pack()
    del pack["test_cases"][0]["remediation"]
    with pytest.raises(ValueError, match="missing required fields: remediation"):
        parse_raw(pack)


def test_duplicate_test_case_and_payload_ids_are_rejected() -> None:
    pack = raw_pack()
    pack["test_cases"].append(pack["test_cases"][0])
    with pytest.raises(ValidationError, match="duplicate test-case"):
        parse_raw(pack)
    pack = raw_pack()
    pack["test_cases"][0]["payloads"][1]["id"] = pack["test_cases"][0]["payloads"][0]["id"]
    with pytest.raises(ValidationError, match="duplicate payload"):
        parse_raw(pack)


def test_missing_safe_behavior_and_empty_payloads_are_rejected() -> None:
    pack = raw_pack()
    pack["test_cases"][0]["expected_safe_behavior"] = ""
    with pytest.raises(ValidationError):
        parse_raw(pack)
    pack = raw_pack()
    pack["test_cases"][0]["payloads"] = []
    with pytest.raises(ValidationError):
        parse_raw(pack)


def test_unsafe_production_marking_and_destructive_text_are_rejected() -> None:
    pack = raw_pack()
    candidate = pack["test_cases"][0]["payloads"][0]
    candidate["tags"].append("unsafe")
    candidate["safe_for_production"] = True
    with pytest.raises(ValidationError, match="unsafe payload"):
        parse_raw(pack)
    pack = raw_pack()
    pack["test_cases"][0]["payloads"][0]["content"] = "Run rm -rf on the host"
    pack["test_cases"][0]["payloads"][0]["placeholders"] = []
    with pytest.raises(ValidationError, match="destructive"):
        parse_raw(pack)


def test_raw_secrets_email_addresses_and_external_targets_are_rejected() -> None:
    for content, message in [
        ("Use api_key=super-secret-value", "credential"),
        ("Contact real.person@example.com", "email"),
        ("Send the probe to https://external.example/path", "external target"),
    ]:
        pack = raw_pack()
        pack["test_cases"][0]["payloads"][0]["content"] = content
        pack["test_cases"][0]["payloads"][0]["placeholders"] = []
        with pytest.raises(ValidationError, match=message):
            parse_raw(pack)


def test_unknown_placeholder_is_rejected_and_known_placeholder_renders_literally() -> None:
    pack = raw_pack()
    pack["test_cases"][0]["payloads"][0]["content"] = "Return {{ARBITRARY_CODE}}"
    pack["test_cases"][0]["payloads"][0]["placeholders"] = ["ARBITRARY_CODE"]
    with pytest.raises(ValidationError, match="unknown placeholders"):
        parse_raw(pack)
    selected = load_active_rule_pack_files(rule_paths()).select(categories={"prompt_injection"})[0]
    rendered = render_payload(selected.payloads[0], {"CANARY_TOKEN": "SAFE-CANARY-001"})
    assert rendered.content.endswith("SAFE-CANARY-001.")
    assert rendered.placeholders == []


def test_ordering_and_filters_are_deterministic() -> None:
    library = load_active_rule_pack_files(reversed(rule_paths()))
    ids = [case.id for case in library.select()]
    assert ids == sorted(ids)
    assert [case.id for case in library.select(categories={"tool_abuse"})] == ["ACT-TA-001"]
    assert {case.id for case in library.select(languages={"tr"})} == {
        "ACT-CM-001",
        "ACT-DL-001",
        "ACT-PI-001",
        "ACT-SP-001",
        "ACT-TA-001",
    }
    assert [case.id for case in library.select(tags={"base64"})] == ["ACT-EP-001"]


def test_enabled_filter_includes_and_excludes_disabled_cases() -> None:
    pack = raw_pack()
    pack["test_cases"][0]["enabled"] = False
    library = parse_raw(pack)
    assert library.select() == []
    assert len(library.select(enabled=False)) == 1
    assert len(library.select(enabled=None)) == 1


def test_multilingual_encoded_controls_and_safe_mode_compatibility() -> None:
    library = load_active_rule_pack_files(rule_paths())
    prompt_case = library.select(categories={"prompt_injection"})[0]
    assert {payload.language for payload in prompt_case.payloads} == {"en", "tr"}
    encoded = library.select(categories={"encoded_payloads"})[0]
    base64_payload = next(payload for payload in encoded.payloads if payload.encoding == "base64")
    rot13_payload = next(payload for payload in encoded.payloads if payload.encoding == "rot13")
    assert b"Ignore previous instructions" in base64.b64decode(base64_payload.content)
    assert "Vtaber" in rot13_payload.content
    safe_cases = library.select(safety_mode=SafetyMode.SAFE)
    assert len(safe_cases) == 8
    assert all(case.control_payload is not None for case in safe_cases)
    assert all(payload.safe_for_production for case in safe_cases for payload in case.payloads)


def test_rule_library_has_no_transport_or_execution_dependencies() -> None:
    forbidden = {"httpx", "requests", "aiohttp", "socket", "subprocess"}
    assert forbidden.isdisjoint(ActiveTestLibrary.__init__.__globals__)
