from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from ragscanner.domain import SourceContent, SourceItem
from ragscanner.parsers import OFFICE_ARCHIVE_MIME_TYPES, OfficeArchiveParser
from ragscanner.pipeline.registry import SUPPORTED_DOCUMENT_EXTENSIONS, ParserRegistry

NOW = datetime(2026, 7, 20, 12, tzinfo=UTC)


def _archive(path: str, xml: bytes) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(path, xml)
    return output.getvalue()


def _source(data: bytes, path: str) -> SourceContent:
    mime = OFFICE_ARCHIVE_MIME_TYPES[Path(path).suffix]
    return SourceContent(
        item=SourceItem(
            id="office-item",
            source_id="local-filesystem",
            external_id=path,
            name=path,
            path=path,
            mime_type=mime,
            size_bytes=len(data),
            modified_at=NOW,
        ),
        content_bytes=data,
        content_type=mime,
        retrieved_at=NOW,
        limit_bytes=max(1, len(data)),
    )


@pytest.mark.parametrize(
    ("path", "member"),
    [
        ("briefing.pptx", "ppt/slides/slide1.xml"),
        ("inventory.xlsx", "xl/sharedStrings.xml"),
        ("policy.odt", "content.xml"),
        ("guide.epub", "OEBPS/chapter1.xhtml"),
    ],
)
def test_office_archive_parser_extracts_inert_text(path: str, member: str) -> None:
    data = _archive(member, b'<root xmlns:a="urn:test"><a:t>Readable content</a:t></root>')

    result = OfficeArchiveParser().parse(_source(data, path))

    assert result.document.normalized_content == "Readable content"
    assert result.document.metadata["active_content_executed"] is False
    assert ParserRegistry.defaults().select(content_type=None, path=path) is not None


def test_supported_document_extensions_include_markdown_and_common_documents() -> None:
    assert {
        ".md",
        ".markdown",
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".odt",
        ".epub",
        ".csv",
        ".json",
        ".yaml",
        ".rst",
        ".html",
        ".htm",
    } <= SUPPORTED_DOCUMENT_EXTENSIONS


def test_office_archive_parser_rejects_malformed_or_oversized_archives() -> None:
    with pytest.raises(ValueError, match="malformed"):
        OfficeArchiveParser().parse(_source(b"not-a-zip", "broken.pptx"))
