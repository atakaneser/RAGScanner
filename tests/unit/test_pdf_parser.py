"""Synthetic, local-only tests for bounded PyMuPDF text extraction."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from ragscanner.domain import SourceContent, SourceItem
from ragscanner.parsers import (
    PAGE_SEPARATOR,
    PdfParser,
    PdfParserConfig,
    PdfParserError,
    PdfParserErrorCategory,
)
from ragscanner.parsers.base import ParserWarning

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def make_pdf(
    pages: list[str | None],
    *,
    metadata: dict[str, str] | None = None,
    image_pages: set[int] | None = None,
    add_link: bool = False,
    javascript: bool = False,
    attachment: bool = False,
    encrypted: bool = False,
) -> bytes:
    document = pymupdf.open()
    image_pages = image_pages or set()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), 0)
    pixmap.clear_with(255)
    image = pixmap.tobytes("png")
    for index, text in enumerate(pages):
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
        if index in image_pages:
            page.insert_image(pymupdf.Rect(72, 90, 92, 110), stream=image)
        if add_link and index == 0:
            page.insert_link(
                {
                    "kind": pymupdf.LINK_URI,
                    "from": pymupdf.Rect(72, 120, 180, 140),
                    "uri": "https://example.invalid/never-fetch",
                }
            )
    if metadata:
        document.set_metadata(metadata)
    if javascript:
        document.xref_set_key(
            document.pdf_catalog(), "OpenAction", "<</S/JavaScript/JS(app.alert)>>"
        )
    if attachment:
        document.embfile_add("synthetic.txt", b"attachment must not be extracted")
    if encrypted:
        result = document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="synthetic-owner",
            user_pw="synthetic-user",
        )
    else:
        result = document.tobytes()
    document.close()
    return result


def empty_pdf() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [] /Count 0 >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, value in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def source(
    data: bytes, *, path: str = "synthetic.pdf", mime: str = "application/pdf"
) -> SourceContent:
    item = SourceItem(
        id="pdf-item",
        source_id="local-filesystem",
        external_id=path,
        name=Path(path).name,
        path=path,
        mime_type=mime,
        size_bytes=len(data),
        modified_at=NOW,
    )
    return SourceContent(
        item=item,
        content_bytes=data,
        content_type=mime,
        retrieved_at=NOW,
        limit_bytes=max(1, len(data)),
    )


def parse(data: bytes, *, config: PdfParserConfig | None = None) -> Any:
    return PdfParser(config=config, clock=lambda: NOW, monotonic_clock=lambda: 0).parse(
        source(data)
    )


def warning_codes(result: Any) -> set[str]:
    return {warning.code for warning in result.warnings}


def test_one_page_text_metadata_and_stable_hash() -> None:
    data = make_pdf(
        ["Hello PDF"],
        metadata={
            "title": "Synthetic title",
            "author": "Synthetic author",
            "creationDate": "D:20260712120000Z",
        },
    )
    first = parse(data)
    second = parse(data)
    assert first.document.title == "Synthetic title"
    assert "Hello PDF" in first.document.content
    assert first.document.content_hash == second.document.content_hash
    assert first.document.source.source_path == "synthetic.pdf"
    assert first.document.metadata["pdf_metadata"]["creation_date"].startswith("2026-07-12")
    assert first.document.metadata["pdf_metadata"]["page_count"] == 1
    assert first.metadata["statistics"]["page_count"] == 1
    assert first.metadata["chunked"] is False


def test_multi_page_order_separator_page_numbers_and_offsets() -> None:
    result = parse(make_pdf(["First page", "Second page", "Third page"]))
    content = result.document.content
    assert content.index("First page") < content.index("Second page") < content.index("Third page")
    assert content.count(PAGE_SEPARATOR) == 2
    pages = result.document.metadata["pages"]
    assert [page["page_number"] for page in pages] == [1, 2, 3]
    for page, expected in zip(pages, ["First page", "Second page", "Third page"], strict=True):
        extracted = content[page["start_offset"] : page["end_offset"]]
        assert expected in extracted
        assert page["character_count"] == len(extracted)
    assert pages[1]["separator_end"] - pages[1]["separator_start"] == len(PAGE_SEPARATOR)


def test_empty_document_empty_page_and_image_only_detection() -> None:
    empty = parse(empty_pdf())
    assert empty.document.content == ""
    assert "no_extractable_text" in warning_codes(empty)
    blank = parse(make_pdf([None]))
    assert {"empty_page", "no_extractable_text"}.issubset(warning_codes(blank))
    image = parse(make_pdf([None], image_pages={0}))
    assert {"empty_page", "no_extractable_text", "likely_scanned_pdf"}.issubset(
        warning_codes(image)
    )
    assert image.metadata["statistics"]["images_detected"] == 1


def test_partially_scanned_pdf_warning() -> None:
    result = parse(make_pdf(["Text page", None], image_pages={1}))
    assert "partially_scanned_pdf" in warning_codes(result)
    assert result.metadata["statistics"]["pages_with_text"] == 1
    assert result.metadata["statistics"]["empty_pages"] == 1


def test_encrypted_malformed_and_unsupported_input_fail_safely() -> None:
    with pytest.raises(PdfParserError) as encrypted:
        parse(make_pdf(["private"], encrypted=True))
    with pytest.raises(PdfParserError) as malformed:
        parse(b"%PDF malformed")
    with pytest.raises(PdfParserError) as unsupported:
        PdfParser().parse(source(b"plain text", path="plain.txt", mime="text/plain"))
    assert encrypted.value.category is PdfParserErrorCategory.ENCRYPTED
    assert malformed.value.category is PdfParserErrorCategory.MALFORMED
    assert unsupported.value.category is PdfParserErrorCategory.UNSUPPORTED


def test_file_page_total_and_per_page_limits() -> None:
    data = make_pdf(["one", "two"])
    with pytest.raises(PdfParserError) as file_limit:
        parse(data, config=PdfParserConfig(maximum_file_size=len(data) - 1))
    with pytest.raises(PdfParserError) as page_count:
        parse(data, config=PdfParserConfig(maximum_page_count=1))
    with pytest.raises(PdfParserError) as per_page:
        parse(make_pdf(["x" * 100]), config=PdfParserConfig(maximum_characters_per_page=10))
    with pytest.raises(PdfParserError) as total:
        parse(
            make_pdf(["123456", "123456"]), config=PdfParserConfig(maximum_extracted_characters=10)
        )
    assert {
        file_limit.value.category,
        page_count.value.category,
        per_page.value.category,
        total.value.category,
    } == {PdfParserErrorCategory.LIMIT_EXCEEDED}


def test_metadata_bounds_malformed_date_and_secret_redaction() -> None:
    result = parse(
        make_pdf(
            ["metadata"],
            metadata={
                "title": "x" * 500,
                "author": "api_key=super-secret-metadata-value",
                "creationDate": "not-a-date",
            },
        ),
        config=PdfParserConfig(maximum_metadata_field_length=64),
    )
    metadata = result.document.metadata["pdf_metadata"]
    assert len(metadata["title"]) <= 64
    assert "super-secret" not in result.model_dump_json()
    assert {"metadata_redacted", "malformed_metadata_date"}.issubset(warning_codes(result))


def test_quality_warnings_are_bounded_non_finding_signals() -> None:
    parser = PdfParser(clock=lambda: NOW, monotonic_clock=lambda: 0)
    warnings: list[ParserWarning] = []
    codes = parser._quality_warnings(
        "\ufffd" + "abc" * 20 + " " * 200 + "\x01" * 20,
        warnings,
        1,
    )
    assert "replacement_characters" in codes
    assert "repeated_garbled_sequence" in codes
    assert "excessive_control_characters" in codes
    assert "excessive_whitespace" in codes
    fragmented = parser._quality_warnings("a\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk\nl\n", warnings, 2)
    assert "fragmented_text" in fragmented
    assert all(warning.page_number in {1, 2} for warning in warnings)


def test_page_number_and_repeated_boilerplate_warnings() -> None:
    numbers = parse(make_pdf(["1", "2"]))
    repeated = parse(make_pdf(["Header", "Header"]))
    assert "page_numbers_only" in warning_codes(numbers)
    assert "repeated_boilerplate_only" in warning_codes(repeated)


def test_multilingual_turkish_english_and_mixed_text() -> None:
    result = parse(make_pdf(["Türkçe içerik", "English content", "Türkçe and English mixed"]))
    assert "Türkçe" in result.document.content
    assert "English" in result.document.content
    assert result.document.language is None


def test_links_javascript_and_attachments_are_only_warned() -> None:
    result = parse(
        make_pdf(
            ["Active content inventory"],
            add_link=True,
            javascript=True,
            attachment=True,
        )
    )
    codes = warning_codes(result)
    assert {
        "embedded_links",
        "embedded_javascript",
        "suspicious_action",
        "embedded_files",
    }.issubset(codes)
    assert result.metadata["active_content_executed"] is False
    assert result.metadata["attachments_extracted"] is False
    assert "attachment must not be extracted" not in result.model_dump_json()


def test_page_separator_collision_is_escaped() -> None:
    data = make_pdf([f"before {PAGE_SEPARATOR} after", "second"])
    result = parse(data)
    assert result.document.content.count(PAGE_SEPARATOR) == 1
    assert "page_separator_escaped" in warning_codes(result)


def test_cooperative_timeout_and_no_network_subprocess_or_logging_dependencies() -> None:
    ticks = iter([0.0, 100.0])
    parser = PdfParser(
        config=PdfParserConfig(timeout_seconds=1),
        clock=lambda: NOW,
        monotonic_clock=lambda: next(ticks),
    )
    with pytest.raises(PdfParserError) as timeout:
        parser.parse(source(make_pdf(["late"])))
    assert timeout.value.category is PdfParserErrorCategory.TIMEOUT
    forbidden = {"httpx", "requests", "socket", "subprocess", "logging", "structlog"}
    assert forbidden.isdisjoint(PdfParser.__init__.__globals__)
