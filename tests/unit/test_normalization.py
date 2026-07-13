"""Focused deterministic tests for document normalization."""

from datetime import UTC, datetime
from typing import Any

import pytest
from ragscanner.domain import Document, SourceLocation
from ragscanner.domain.helpers import document_content_hash
from ragscanner.normalization import (
    AnnotationType,
    DocumentNormalizer,
    NormalizationConfig,
    NormalizationError,
    NormalizationErrorCategory,
    UnicodeForm,
)
from ragscanner.parsers import BLOCK_SEPARATOR, PAGE_SEPARATOR

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def document(
    content: str,
    *,
    mime: str = "text/plain",
    metadata: dict[str, Any] | None = None,
    content_hash: str | None = None,
) -> Document:
    return Document(
        id="document-1",
        source=SourceLocation(
            source_id="source-1",
            source_type="filesystem",
            source_name="local",
            source_path="synthetic.txt",
            line_start=1,
            line_end=max(1, content.count("\n") + 1),
        ),
        content=content,
        normalized_content="parser-owned-value",
        content_hash=content_hash or document_content_hash(content),
        mime_type=mime,
        ingested_at=NOW,
        metadata=metadata or {},
    )


def normalize(content: str, **config: Any):  # type: ignore[no-untyped-def]
    return DocumentNormalizer(NormalizationConfig(**config)).normalize(document(content))


def annotation_types(result) -> set[AnnotationType]:  # type: ignore[no-untyped-def]
    return {annotation.annotation_type for annotation in result.annotations}


def pdf_document(pages: list[str]) -> Document:
    parts: list[str] = []
    metadata: list[dict[str, Any]] = []
    offset = 0
    for index, page in enumerate(pages):
        separator_start = separator_end = None
        if index:
            separator_start = offset
            parts.append(PAGE_SEPARATOR)
            offset += len(PAGE_SEPARATOR)
            separator_end = offset
        start = offset
        parts.append(page)
        offset += len(page)
        metadata.append(
            {
                "page_number": index + 1,
                "start_offset": start,
                "end_offset": offset,
                "separator_start": separator_start,
                "separator_end": separator_end,
            }
        )
    return document("".join(parts), mime="application/pdf", metadata={"pages": metadata})


def test_crlf_cr_and_original_content_are_preserved_separately() -> None:
    source = document("a\r\nb\rc")
    result = DocumentNormalizer().normalize(source)
    assert result.normalized_content == "a\nb\nc"
    assert source.content == "a\r\nb\rc"
    assert source.normalized_content == "parser-owned-value"
    assert result.statistics.newline_changes == 2


def test_default_nfc_preserves_turkish_multilingual_and_emoji() -> None:
    raw = "I\u0307stanbul, Tu\u0308rkc\u0327e, العربية, 日本語 👩‍💻"
    result = normalize(raw)
    assert "İstanbul" in result.normalized_content
    assert "Türkçe" in result.normalized_content
    assert "العربية" in result.normalized_content
    assert "日本語" in result.normalized_content
    assert "👩‍💻" in result.normalized_content
    assert result.metadata["unicode_form"] == "NFC"


def test_nfkc_is_explicit_and_records_compatibility_changes() -> None:
    nfc = normalize("ＡＢＣ ①", unicode_form=UnicodeForm.NFC)
    nfkc = normalize("ＡＢＣ ①", unicode_form=UnicodeForm.NFKC)
    assert nfc.normalized_content == "ＡＢＣ ①"
    assert nfkc.normalized_content == "ABC 1"
    assert nfkc.statistics.unicode_changes > 0


@pytest.mark.parametrize(
    ("raw", "marker", "annotation"),
    [
        ("a\u200bb", "<ZWSP>", AnnotationType.INVISIBLE_UNICODE),
        ("a\u202eb", "<BIDI:RLO>", AnnotationType.BIDI_CONTROL),
        ("a\x00b", "<NUL>", AnnotationType.INVISIBLE_UNICODE),
        ("a\ufffdb", "<REPLACEMENT>", AnnotationType.REPLACEMENT_CHARACTER),
        ("a\u00adb", "<SOFT_HYPHEN>", AnnotationType.INVISIBLE_UNICODE),
    ],
)
def test_security_sensitive_invisible_characters_are_visible_and_annotated(
    raw: str, marker: str, annotation: AnnotationType
) -> None:
    result = normalize(raw)
    assert marker in result.normalized_content
    assert annotation in annotation_types(result)
    assert "security_sensitive_control" in {warning.code for warning in result.warnings}
    segment = next(
        segment
        for segment in result.segments
        if "visible_control_marker" in segment.transformation_types
    )
    assert segment.approximate is True


def test_conservative_spaces_trailing_whitespace_and_blank_lines() -> None:
    result = normalize("one   two  \n\n\n\nthree\t\tend\t")
    assert result.normalized_content == "one two\n\n\nthree end"
    assert result.statistics.whitespace_changes >= 3
    assert result.statistics.blank_lines_removed == 1


def test_markdown_fenced_and_indented_code_preserve_whitespace() -> None:
    content = "Text   here\n```python\nx  =  1  \n```\n    a   b  \n"
    result = DocumentNormalizer().normalize(document(content, mime="text/markdown"))
    assert "Text here" in result.normalized_content
    assert "x  =  1  " in result.normalized_content
    assert "    a   b  " in result.normalized_content
    assert AnnotationType.CODE_REGION in annotation_types(result)


def test_table_and_ascii_diagram_spacing_is_preserved() -> None:
    content = "| A  | B   |\n+----+    +----+\nordinary   text"
    result = normalize(content)
    assert "| A  | B   |" in result.normalized_content
    assert "+----+    +----+" in result.normalized_content
    assert "ordinary text" in result.normalized_content
    assert AnnotationType.TABLE_REGION in annotation_types(result)


def test_pdf_visual_wrap_repair_is_explainable_and_bounded() -> None:
    source = pdf_document(
        ["This is a sufficiently long visual line that\ncontinues naturally here."]
    )
    result = DocumentNormalizer().normalize(source)
    assert "that continues naturally" in result.normalized_content
    assert result.statistics.pdf_wrap_repairs == 1
    assert any(
        "pdf_line_wrap_repair" in segment.transformation_types for segment in result.segments
    )


@pytest.mark.parametrize(
    "content",
    [
        "Paragraph ends here.\nnext paragraph starts",
        "# Heading\ncontinuation",
        "- first item\n- second item",
        "Name  Value  Count\nA     B      C",
    ],
)
def test_pdf_wrap_preserves_paragraph_heading_list_and_table_boundaries(content: str) -> None:
    result = DocumentNormalizer().normalize(pdf_document([content]))
    assert "\n" in result.normalized_content
    assert result.statistics.pdf_wrap_repairs == 0


def test_high_confidence_hyphen_repair_and_mapping() -> None:
    result = DocumentNormalizer().normalize(pdf_document(["The extracted informa-\ntion remains."]))
    assert "information" in result.normalized_content
    assert result.statistics.hyphenated_line_repairs == 1
    assert any(segment.approximate for segment in result.segments)


@pytest.mark.parametrize(
    "content",
    [
        "A state-of-the-art method stays intact.",
        "https://example.invalid/informa-\ntion",
        "/var/lib/informa-\ntion",
        "item-\n- next bullet",
        "value = informa-\ntion;",
    ],
)
def test_hyphen_repair_preserves_legitimate_hyphens_urls_paths_lists_and_code(content: str) -> None:
    result = DocumentNormalizer().normalize(pdf_document([content]))
    assert result.statistics.hyphenated_line_repairs == 0


def test_cross_page_join_is_prevented_and_page_marker_preserved() -> None:
    result = DocumentNormalizer().normalize(
        pdf_document(["This is a sufficiently long unfinished line", "continuation on next page"])
    )
    assert PAGE_SEPARATOR in result.normalized_content
    assert result.statistics.pdf_wrap_repairs == 0


def test_repeated_headers_footers_page_numbers_are_candidates_not_removed() -> None:
    source = pdf_document(
        [
            "CONFIDENTIAL\nFirst body.\nPage 1",
            "CONFIDENTIAL\nSecond body.\nPage 2",
            "CONFIDENTIAL\nThird body.\nPage 3",
        ]
    )
    result = DocumentNormalizer().normalize(source)
    types = annotation_types(result)
    assert AnnotationType.HEADER_CANDIDATE in types
    assert AnnotationType.PAGE_NUMBER_CANDIDATE in types
    assert "CONFIDENTIAL" in result.normalized_content
    assert "Page 2" in result.normalized_content
    assert result.metadata["boilerplate_removed"] is False


def test_repeated_footer_candidate_is_detected_without_removal() -> None:
    source = pdf_document(
        [
            "First body.\nInternal use only",
            "Second body.\nInternal use only",
            "Third body.\nInternal use only",
        ]
    )
    result = DocumentNormalizer().normalize(source)
    footer = next(
        item
        for item in result.annotations
        if item.annotation_type is AnnotationType.FOOTER_CANDIDATE
    )
    assert footer.occurrence_count == 3
    assert footer.pages == [1, 2, 3]
    assert "Internal use only" in result.normalized_content


def test_docx_structure_annotations_and_boundaries_survive() -> None:
    content = f"Title{BLOCK_SEPARATOR}Item{BLOCK_SEPARATOR}Cell"
    blocks = [
        {
            "block_index": 0,
            "block_type": "heading",
            "start_offset": 0,
            "end_offset": 5,
            "section_index": 0,
            "region": "body",
        },
        {
            "block_index": 1,
            "block_type": "list_item",
            "start_offset": 5 + len(BLOCK_SEPARATOR),
            "end_offset": 9 + len(BLOCK_SEPARATOR),
            "section_index": 0,
            "region": "body",
        },
        {
            "block_index": 2,
            "block_type": "table_cell",
            "start_offset": 9 + 2 * len(BLOCK_SEPARATOR),
            "end_offset": len(content),
            "section_index": 0,
            "region": "body",
        },
    ]
    result = DocumentNormalizer().normalize(
        document(
            content,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            metadata={"blocks": blocks},
        )
    )
    assert BLOCK_SEPARATOR in result.normalized_content
    assert {
        AnnotationType.HEADING_REGION,
        AnnotationType.LIST_REGION,
        AnnotationType.TABLE_REGION,
    }.issubset(annotation_types(result))


def test_markdown_heading_annotation_is_preserved_as_metadata() -> None:
    source = document(
        "# Başlık\nMetin",
        mime="text/markdown",
        metadata={"headings": [{"line": 1, "level": 1, "text": "Başlık"}]},
    )
    result = DocumentNormalizer().normalize(source)
    heading = next(
        item
        for item in result.annotations
        if item.annotation_type is AnnotationType.HEADING_REGION and "level" in item.metadata
    )
    assert heading.metadata["level"] == 1
    assert result.normalized_content.startswith("# Başlık")


def test_source_segments_map_to_original_lines_pages_and_blocks() -> None:
    source = pdf_document(["first   line", "second page"])
    result = DocumentNormalizer().normalize(source)
    assert result.segments
    assert {
        segment.source_location.page_number
        for segment in result.segments
        if segment.source_location.page_number
    } == {1, 2}
    assert all(
        segment.source_location.source_path == "synthetic.txt" for segment in result.segments
    )
    collapsed = next(
        segment
        for segment in result.segments
        if "horizontal_whitespace" in segment.transformation_types
    )
    assert collapsed.approximate is True
    assert source.content[collapsed.original_start : collapsed.original_end] == "   "


def test_hash_and_complete_result_are_deterministic() -> None:
    source = document("Cafe\u0301   metin\u200b")
    normalizer = DocumentNormalizer()
    first = normalizer.normalize(source)
    second = normalizer.normalize(source)
    assert first == second
    assert first.normalized_hash == document_content_hash(first.normalized_content)
    idempotent = normalizer.normalize(document(first.normalized_content))
    assert idempotent.normalized_content == first.normalized_content


def test_output_annotation_and_segment_limits_are_safe() -> None:
    with pytest.raises(NormalizationError) as output:
        normalize("123456", maximum_normalized_output_size=5)
    assert output.value.category is NormalizationErrorCategory.OUTPUT_LIMIT_EXCEEDED
    annotated = normalize("\u200b\u200c\u200d", maximum_annotations=2)
    assert len(annotated.annotations) == 2
    assert "annotation_limit_reached" in {warning.code for warning in annotated.warnings}
    segmented = normalize("a\u200bb\u202ec", maximum_normalization_segments=2)
    assert len(segmented.segments) <= 2
    assert "segment_limit_coalesced" in {warning.code for warning in segmented.warnings}
    assert any(segment.approximate for segment in segmented.segments)


def test_malformed_hash_fails_closed_and_empty_document_is_valid() -> None:
    malformed = document("content", content_hash="0" * 64)
    with pytest.raises(NormalizationError) as caught:
        DocumentNormalizer().normalize(malformed)
    assert caught.value.category is NormalizationErrorCategory.INVALID_INPUT
    empty = DocumentNormalizer().normalize(document(""))
    assert empty.normalized_content == ""
    assert empty.normalized_hash == document_content_hash("")


def test_pipeline_has_no_network_or_subprocess_surface() -> None:
    result = normalize("No links are fetched: https://example.invalid and no code runs.")
    assert "https://example.invalid" in result.normalized_content
    assert "network" not in result.metadata
    assert "subprocess" not in result.metadata
