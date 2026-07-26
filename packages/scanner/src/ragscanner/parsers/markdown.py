"""Non-rendering Markdown parser with bounded scalar front matter extraction."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from ragscanner.domain import SourceContent
from ragscanner.domain.helpers import (
    REDACTED,
    contains_unreferenced_secret,
    mask_secret_like_values,
)
from ragscanner.parsers.base import (
    ParserResult,
    ParserWarning,
    build_document,
    decode_source,
    normalize_newlines,
)

_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FRONT_MATTER_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")


class MarkdownParser:
    name = "markdown"
    version = "1.1.0"

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def parse(self, source: SourceContent) -> ParserResult:
        if source.item.mime_type != "text/markdown" and source.content_type != "text/markdown":
            raise ValueError("Markdown parser requires text/markdown content")
        content, warnings = decode_source(source)
        normalized = normalize_newlines(content)
        front_matter, body_start, front_warnings = self._front_matter(normalized)
        warnings.extend(front_warnings)
        headings = self._headings(normalized.splitlines(), body_start)
        title = front_matter.get("title")
        if not title:
            first_h1 = next(
                (heading["text"] for heading in headings if heading["level"] == 1), None
            )
            title = (
                str(first_h1)
                if first_h1
                else PurePosixPath(source.item.path or source.item.name).stem
            )
        document = build_document(
            source,
            content=content,
            normalized_content=normalized,
            title=str(title),
            mime_type="text/markdown",
            metadata={
                "front_matter": front_matter,
                "headings": headings,
                "markdown_untrusted": True,
                "rendered": False,
            },
            warnings=warnings,
            clock=self._clock(),
        )
        return ParserResult(
            document=document,
            warnings=warnings,
            parser_name=self.name,
            parser_version=self.version,
            source_item_id=source.item.id,
            metadata={"chunked": False, "html_rendered": False, "links_fetched": False},
        )

    @staticmethod
    def _front_matter(content: str) -> tuple[dict[str, str], int, list[ParserWarning]]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, 0, []
        closing = next(
            (index for index, line in enumerate(lines[1:101], start=1) if line.strip() == "---"),
            None,
        )
        if closing is None or sum(len(line) for line in lines[:101]) > 16_384:
            return (
                {},
                0,
                [
                    ParserWarning(
                        code="front_matter_unterminated",
                        message="Front matter was not parsed because it was unterminated or too large.",
                    )
                ],
            )
        values: dict[str, str] = {}
        warnings: list[ParserWarning] = []
        for line_number, line in enumerate(lines[1:closing], start=2):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if ":" not in line:
                warnings.append(
                    ParserWarning(
                        code="front_matter_unsupported",
                        message="A non-scalar front matter line was ignored.",
                        line=line_number,
                    )
                )
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip()
            if not _FRONT_MATTER_KEY.fullmatch(key):
                warnings.append(
                    ParserWarning(
                        code="front_matter_key_ignored",
                        message="An invalid front matter key was ignored.",
                        line=line_number,
                    )
                )
                continue
            value = raw_value.strip().strip("\"'")[:1024]
            values[key] = (
                REDACTED
                if contains_unreferenced_secret(value, parent_key=key)
                else mask_secret_like_values(value)
            )
        return values, closing + 1, warnings

    @staticmethod
    def _headings(lines: list[str], body_start: int) -> list[dict[str, Any]]:
        headings: list[dict[str, Any]] = []
        fence: str | None = None
        for line_number, line in enumerate(lines[body_start:], start=body_start + 1):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                marker = stripped[:3]
                fence = None if fence == marker else marker if fence is None else fence
                continue
            if fence is not None:
                continue
            match = _HEADING.match(line)
            if match:
                headings.append(
                    {
                        "level": len(match.group(1)),
                        "text": mask_secret_like_values(match.group(2).strip()),
                        "line": line_number,
                    }
                )
        return headings
