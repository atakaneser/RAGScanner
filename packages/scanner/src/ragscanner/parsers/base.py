"""Framework-independent parser result and parser protocol."""

import hashlib
import html
import re
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator

from ragscanner.domain import Document, SourceContent, SourceLocation
from ragscanner.domain.helpers import contains_unreferenced_secret, document_content_hash

_SEMICOLON_HTML_CHARACTER_REFERENCE = re.compile(
    r"&(?:#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});"
)


class ParserWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    page_number: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        if contains_unreferenced_secret(value):
            raise ValueError("parser warning metadata cannot contain credentials")
        return value


class ParserResult(BaseModel):
    document: Document
    warnings: list[ParserWarning] = Field(default_factory=list)
    parser_name: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class DocumentParser(Protocol):
    def parse(self, source: SourceContent) -> ParserResult: ...


def decode_source(source: SourceContent) -> tuple[str, list[ParserWarning]]:
    encoding = source.encoding or "utf-8"
    replacement = any(
        warning.code == "decoding_replacement_required" for warning in source.warnings
    )
    try:
        text = source.content_bytes.decode(encoding, errors="replace" if replacement else "strict")
    except (LookupError, UnicodeDecodeError) as error:
        raise ValueError("source content cannot be decoded with its declared encoding") from error
    warnings = [
        ParserWarning(code=warning.code, message=warning.message) for warning in source.warnings
    ]
    if replacement:
        warnings.append(
            ParserWarning(
                code="replacement_characters", message="Malformed byte sequences were replaced."
            )
        )
    if source.metadata.get("upstream") == "openwebui":
        text = _decode_semicolon_html_character_references_once(text)
    return text, warnings


def _decode_semicolon_html_character_references_once(value: str) -> str:
    """Restore character references introduced by an OpenWebUI text transport."""

    return _SEMICOLON_HTML_CHARACTER_REFERENCE.sub(
        lambda match: html.unescape(match.group(0)),
        value,
    )


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def build_document(
    source: SourceContent,
    *,
    content: str,
    normalized_content: str,
    title: str | None,
    mime_type: str,
    metadata: dict[str, Any],
    warnings: list[ParserWarning],
    clock: datetime | None = None,
    language: str | None = None,
) -> Document:
    line_count = max(1, normalized_content.count("\n") + 1)
    item = source.item
    return Document(
        id=hashlib.sha256(
            f"document:v1:{item.id}:{document_content_hash(content)}".encode()
        ).hexdigest(),
        source=SourceLocation(
            source_id=item.source_id,
            source_type="filesystem",
            source_name=item.source_id,
            source_path=item.path,
            line_start=1,
            line_end=line_count,
        ),
        title=title,
        content=content,
        normalized_content=normalized_content,
        content_hash=document_content_hash(content),
        mime_type=mime_type,
        language=language,
        created_at=item.created_at,
        modified_at=item.modified_at,
        ingested_at=clock or datetime.now(UTC),
        metadata=metadata,
        warnings=[warning.message for warning in warnings],
    )
