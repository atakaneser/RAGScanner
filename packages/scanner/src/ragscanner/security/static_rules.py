"""Safe JSON loading, validation, and filtering for static rule packs."""

import json
import re
from collections.abc import Iterable
from pathlib import Path

from ragscanner.security.static_models import (
    MatcherType,
    StaticRule,
    StaticRulePack,
    StaticRuleSelection,
)

_UNSAFE_REGEX = (
    re.compile(r"\\[1-9]"),
    re.compile(r"\(\?(?:[=!<]|P[=<])"),
    re.compile(r"(?:\*|\+|\{\d+,?\})\s*(?:\*|\+|\{\d+,?\})"),
    re.compile(r"\([^)]*(?:\*|\+)[^)]*\)(?:\*|\+|\{\d+,?\})"),
)


def validate_safe_regex(pattern: str) -> re.Pattern[str]:
    if any(unsafe.search(pattern) for unsafe in _UNSAFE_REGEX):
        raise ValueError("static rule contains an unsupported high-risk regex construct")
    try:
        return re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    except re.error as error:
        raise ValueError("static rule contains an invalid regular expression") from error


class StaticRuleLibrary:
    def __init__(self, packs: Iterable[StaticRulePack]) -> None:
        self._packs = tuple(
            sorted((pack.model_copy(deep=True) for pack in packs), key=lambda p: p.pack_id)
        )
        rules = [rule for pack in self._packs for rule in pack.rules]
        ids = [rule.id for rule in rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate static rule ID across packs")
        for rule in rules:
            for matcher in rule.matchers:
                if matcher.type is MatcherType.REGEX:
                    for pattern in matcher.patterns:
                        validate_safe_regex(pattern)
                if (
                    matcher.type
                    in {
                        MatcherType.EXACT,
                        MatcherType.SUBSTRING_CI,
                        MatcherType.REGEX,
                        MatcherType.TOKEN_SEQUENCE,
                        MatcherType.DECODED_CONTENT,
                        MatcherType.METADATA_FIELD,
                    }
                    and not matcher.patterns
                ):
                    raise ValueError(f"matcher for {rule.id} requires patterns")
        self._rules = tuple(
            sorted((rule.model_copy(deep=True) for rule in rules), key=lambda r: r.id)
        )

    @property
    def pack_versions(self) -> list[str]:
        return [f"{pack.pack_id}@{pack.version}" for pack in self._packs]

    @classmethod
    def from_texts(cls, texts: Iterable[str | bytes]) -> "StaticRuleLibrary":
        packs: list[StaticRulePack] = []
        for text in texts:
            try:
                raw = json.loads(text)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("invalid static rule-pack JSON") from error
            packs.append(StaticRulePack.model_validate(raw))
        return cls(packs)

    @classmethod
    def from_directory(cls, directory: Path) -> "StaticRuleLibrary":
        if not directory.is_dir():
            raise ValueError("static rule directory does not exist")
        files = sorted(directory.glob("*.json"))
        if not files:
            raise ValueError("static rule directory contains no JSON rule packs")
        return cls.from_texts(path.read_bytes() for path in files)

    def select(self, selection: StaticRuleSelection) -> tuple[list[StaticRule], list[str]]:
        selected: list[StaticRule] = []
        skipped: list[str] = []
        for rule in self._rules:
            include_disabled = selection.include_disabled or (
                selection.include_pii and rule.category == "pii"
            )
            accepted = True
            if not rule.enabled and not include_disabled:
                accepted = False
            if rule.id in selection.excluded_rule_ids:
                accepted = False
            if selection.rule_ids and rule.id not in selection.rule_ids:
                accepted = False
            if selection.categories and rule.category not in selection.categories:
                accepted = False
            if selection.severities and rule.severity not in selection.severities:
                accepted = False
            if selection.tags and not selection.tags.intersection(rule.tags):
                accepted = False
            if selection.languages and not selection.languages.intersection(rule.languages):
                accepted = False
            if selection.scopes and not selection.scopes.intersection(rule.scope):
                accepted = False
            if accepted:
                selected.append(rule.model_copy(deep=True))
            else:
                skipped.append(rule.id)
        return selected, skipped
