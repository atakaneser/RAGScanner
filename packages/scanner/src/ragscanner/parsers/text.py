"""Plain-text parser with safe decoding and newline normalization."""

from collections.abc import Callable
from datetime import UTC, datetime

from ragscanner.domain import SourceContent
from ragscanner.parsers.base import (
    ParserResult,
    build_document,
    decode_source,
    normalize_newlines,
)


class PlainTextParser:
    name = "plain_text"
    version = "1.0.0"

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def parse(self, source: SourceContent) -> ParserResult:
        if source.item.mime_type != "text/plain" and source.content_type != "text/plain":
            raise ValueError("plain-text parser requires text/plain content")
        content, warnings = decode_source(source)
        normalized = normalize_newlines(content)
        document = build_document(
            source,
            content=content,
            normalized_content=normalized,
            title=None,
            mime_type="text/plain",
            metadata={"line_count": max(1, normalized.count("\n") + 1)},
            warnings=warnings,
            clock=self._clock(),
        )
        return ParserResult(
            document=document,
            warnings=warnings,
            parser_name=self.name,
            parser_version=self.version,
            source_item_id=source.item.id,
            metadata={"chunked": False},
        )
