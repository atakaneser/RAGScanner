"""Vendor-neutral deterministic token approximation."""

import re

from ragscanner.chunking.models import TokenSpan

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class WhitespaceTokenCounter:
    name = "unicode_word_punctuation_approximation"
    version = "1.0.0"

    def spans(self, text: str) -> list[TokenSpan]:
        return [TokenSpan(start=match.start(), end=match.end()) for match in _TOKEN.finditer(text)]

    def count(self, text: str) -> int:
        return sum(1 for _ in _TOKEN.finditer(text))
