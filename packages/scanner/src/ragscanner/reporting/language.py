"""Conservative report-language inference for single-language source collections."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

_SUPPORTED = frozenset({"en", "tr", "de", "fr", "zh-CN", "it"})
_STOPWORDS = {
    "en": frozenset(
        {"and", "the", "for", "with", "this", "that", "from", "your", "you", "is", "are"}
    ),
    "tr": frozenset(
        {
            "bir",
            "bu",
            "ve",
            "ile",
            "için",
            "olarak",
            "sonra",
            "gerekir",
            "üzerinden",
            "de",
            "da",
        }
    ),
    "de": frozenset(
        {"und", "der", "die", "das", "für", "mit", "ist", "sind", "von", "nach", "ein"}
    ),
    "fr": frozenset({"et", "le", "la", "les", "pour", "avec", "est", "sont", "des", "une", "dans"}),
    "it": frozenset({"e", "il", "la", "per", "con", "è", "sono", "dei", "una", "nel", "dopo"}),
}


def _normalize_declared(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().replace("_", "-")
    lowered = normalized.casefold()
    if lowered.startswith("zh"):
        return "zh-CN"
    short = lowered.split("-", 1)[0]
    return short if short in _SUPPORTED else None


def infer_report_language(
    contents: Iterable[tuple[str, str | None]],
    *,
    fallback: str = "en",
) -> str:
    """Infer one supported language, otherwise preserve the caller's explicit fallback."""

    entries = list(contents)
    declared = Counter(
        language
        for _content, raw_language in entries
        if (language := _normalize_declared(raw_language)) is not None
    )
    if declared:
        language, count = declared.most_common(1)[0]
        if count * 2 >= sum(declared.values()):
            return language

    sample = "\n".join(content[:20_000] for content, _language in entries)[:80_000]
    if len(re.findall(r"[\u3400-\u9fff]", sample)) >= 20:
        return "zh-CN"
    words = re.findall(r"[^\W\d_]+", sample.casefold(), flags=re.UNICODE)
    scores = Counter(
        {
            language: sum(word in stopwords for word in words)
            for language, stopwords in _STOPWORDS.items()
        }
    )
    ranked = scores.most_common(2)
    if ranked and ranked[0][1] >= 6:
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        if ranked[0][1] >= runner_up + 2:
            return ranked[0][0]
    return fallback if fallback in _SUPPORTED else "en"
