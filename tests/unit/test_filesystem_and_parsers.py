"""Temporary-directory tests for the local connector and TXT/Markdown parsers."""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from ragscanner.connectors.filesystem import (
    EncodingStrategy,
    FilesystemSourceConfig,
    LocalFilesystemConnector,
)
from ragscanner.domain import SourceChangeType, SourceConnector, SourceError, SourceErrorCategory
from ragscanner.parsers import MarkdownParser, PlainTextParser

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def connector(root: Path, **changes: object) -> LocalFilesystemConnector:
    values: dict[str, object] = {"root_path": root}
    values.update(changes)
    return LocalFilesystemConnector(FilesystemSourceConfig(**values))


async def all_items(source: LocalFilesystemConnector, page_size: int = 100) -> list[object]:
    items: list[object] = []
    cursor = None
    while True:
        page = await source.list_items(cursor, page_size)
        items.extend(page.items)
        if not page.has_more:
            return items
        cursor = page.next_cursor


def test_recursive_non_recursive_supported_and_hidden_discovery(tmp_path: Path) -> None:
    (tmp_path / "root.txt").write_text("root")
    (tmp_path / "document.pdf").write_bytes(b"pdf")
    (tmp_path / ".hidden.md").write_text("hidden")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "guide.markdown").write_text("nested")
    recursive = asyncio.run(all_items(connector(tmp_path)))
    assert [item.path for item in recursive] == [
        "document.pdf",
        "nested/guide.markdown",
        "root.txt",
    ]
    flat = asyncio.run(all_items(connector(tmp_path, recursive=False)))
    assert [item.path for item in flat] == ["document.pdf", "root.txt"]


@pytest.mark.parametrize(
    "filename",
    [
        "Türkçe bilgi (2026).txt",
        "Deutsche Äußerung.md",
        "مستند عربي.txt",
        "Документ.txt",
        "知识库 📘.md",
        "Cafe\u0301 guide.txt",
    ],
)
def test_unicode_and_shell_sensitive_filenames_are_discovered_and_read(
    tmp_path: Path, filename: str
) -> None:
    path = tmp_path / filename
    path.write_text("Synthetic multilingual path fixture.", encoding="utf-8")

    source = connector(tmp_path)
    items = asyncio.run(all_items(source))

    assert len(items) == 1
    content = asyncio.run(source.get_content(items[0].id, 1_024))
    assert content.content_bytes == b"Synthetic multilingual path fixture."


def test_include_exclude_ordering_and_pagination(tmp_path: Path) -> None:
    for name in ["z.txt", "a.md", "b.txt", "skip.txt"]:
        (tmp_path / name).write_text(name)
    source = connector(tmp_path, include_patterns=["*.txt"], exclude_patterns=["skip*"])
    first = asyncio.run(source.list_items(None, 1))
    second = asyncio.run(source.list_items(first.next_cursor, 1))
    assert [first.items[0].path, second.items[0].path] == ["b.txt", "z.txt"]
    assert second.has_more is False
    assert [item.path for item in asyncio.run(all_items(source))] == ["b.txt", "z.txt"]


def test_empty_utf8_bom_and_fallback_content(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "bom.txt").write_bytes(b"\xef\xbb\xbfhello")
    (tmp_path / "turkish.txt").write_bytes("Türkçe içerik".encode("cp1254"))
    source = connector(
        tmp_path, encoding_strategy=EncodingStrategy.FALLBACK, fallback_encodings=["cp1254"]
    )
    items = {item.name: item for item in asyncio.run(all_items(source))}
    empty = asyncio.run(source.get_content(items["empty.txt"].id, 100))
    bom = asyncio.run(source.get_content(items["bom.txt"].id, 100))
    fallback = asyncio.run(source.get_content(items["turkish.txt"].id, 100))
    assert empty.content_bytes == b""
    assert bom.encoding == "utf-8-sig"
    assert fallback.encoding == "cp1254"
    assert fallback.warnings[0].code == "fallback_encoding"


def test_malformed_replacement_binary_and_oversized_fail_safely(tmp_path: Path) -> None:
    (tmp_path / "malformed.txt").write_bytes(b"hello\xff")
    (tmp_path / "binary.txt").write_bytes(b"\x00\x01\x02binary")
    (tmp_path / "large.txt").write_bytes(b"123456")
    strict = connector(tmp_path, maximum_file_size=5)
    items = {item.name: item for item in asyncio.run(all_items(strict))}
    with pytest.raises(SourceError) as malformed:
        asyncio.run(strict.get_content(items["malformed.txt"].id, 100))
    with pytest.raises(SourceError) as binary:
        asyncio.run(strict.get_content(items["binary.txt"].id, 100))
    with pytest.raises(SourceError) as large:
        asyncio.run(strict.get_content(items["large.txt"].id, 100))
    assert malformed.value.detail.category is SourceErrorCategory.CONTENT_TOO_LARGE
    assert binary.value.detail.category is SourceErrorCategory.CONTENT_TOO_LARGE
    assert large.value.detail.category is SourceErrorCategory.CONTENT_TOO_LARGE
    replacement = connector(
        tmp_path, maximum_file_size=100, encoding_strategy=EncodingStrategy.REPLACE
    )
    replacement_item = next(
        item for item in asyncio.run(all_items(replacement)) if item.name == "malformed.txt"
    )
    content = asyncio.run(replacement.get_content(replacement_item.id, 100))
    assert content.warnings[0].code == "decoding_replacement_required"


def test_binary_and_malformed_categories_with_sufficient_size_limit(tmp_path: Path) -> None:
    (tmp_path / "binary.txt").write_bytes(b"\x00binary")
    (tmp_path / "malformed.txt").write_bytes(b"text\xff")
    source = connector(tmp_path, maximum_file_size=100)
    items = {item.name: item for item in asyncio.run(all_items(source))}
    with pytest.raises(SourceError) as binary:
        asyncio.run(source.get_content(items["binary.txt"].id, 100))
    with pytest.raises(SourceError) as malformed:
        asyncio.run(source.get_content(items["malformed.txt"].id, 100))
    assert binary.value.detail.category is SourceErrorCategory.MALFORMED_RESPONSE
    assert malformed.value.detail.category is SourceErrorCategory.MALFORMED_RESPONSE


def test_root_validation_missing_root_and_root_as_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        FilesystemSourceConfig(root_path=Path("relative"))
    with pytest.raises(ValidationError):
        FilesystemSourceConfig(root_path=Path(Path.cwd().anchor))
    missing = connector(tmp_path / "missing")
    with pytest.raises(SourceError) as missing_error:
        asyncio.run(missing.list_items(None, 10))
    root_file = tmp_path / "root.txt"
    root_file.write_text("content")
    with pytest.raises(SourceError) as file_error:
        asyncio.run(connector(root_file).list_items(None, 10))
    assert missing_error.value.detail.category is SourceErrorCategory.NOT_FOUND
    assert file_error.value.detail.category is SourceErrorCategory.CONFIGURATION


def test_path_traversal_and_symlink_policy(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    link = root / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable")
    default = connector(root)
    page = asyncio.run(default.list_items(None, 10))
    assert page.items == []
    assert any(warning.code == "symlink_skipped" for warning in page.warnings)
    with pytest.raises(SourceError) as escaped:
        asyncio.run(connector(root, follow_symlinks=True).list_items(None, 10))
    with pytest.raises(SourceError) as traversal:
        asyncio.run(default.get_item("../outside.txt"))
    assert escaped.value.detail.category is SourceErrorCategory.AUTHORIZATION
    assert traversal.value.detail.category is SourceErrorCategory.NOT_FOUND


def test_internal_symlink_can_be_explicitly_followed(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("inside")
    link = tmp_path / "alias.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    items = asyncio.run(all_items(connector(tmp_path, follow_symlinks=True)))
    assert [item.path for item in items] == ["alias.txt", "target.txt"]
    alias = next(item for item in items if item.path == "alias.txt")
    assert (
        asyncio.run(
            connector(tmp_path, follow_symlinks=True).get_content(alias.id, 100)
        ).content_bytes
        == b"inside"
    )


def test_broken_symlink_and_unreadable_file_fail_safely_where_portable(tmp_path: Path) -> None:
    broken = tmp_path / "broken.txt"
    try:
        broken.symlink_to(tmp_path / "missing-target.txt")
    except OSError:
        pytest.skip("symlinks are unavailable")
    page = asyncio.run(connector(tmp_path, follow_symlinks=True).list_items(None, 10))
    assert any(warning.code == "broken_symlink" for warning in page.warnings)

    protected = tmp_path / "protected.txt"
    protected.write_text("protected")
    source = connector(tmp_path)
    item = next(item for item in asyncio.run(all_items(source)) if item.name == "protected.txt")
    protected.chmod(0)
    try:
        try:
            asyncio.run(source.get_content(item.id, 100))
        except SourceError as error:
            assert error.detail.category in {
                SourceErrorCategory.AUTHORIZATION,
                SourceErrorCategory.UNAVAILABLE,
            }
        else:
            pytest.skip("current platform or user can read mode-000 files")
    finally:
        protected.chmod(0o600)


def test_non_regular_fifo_is_skipped_where_supported(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe.txt"
    if not hasattr(os, "mkfifo"):
        pytest.skip("named pipes are unavailable")
    os.mkfifo(fifo)
    page = asyncio.run(connector(tmp_path).list_items(None, 10))
    assert page.items == []
    assert any(warning.code == "special_file_skipped" for warning in page.warnings)


def test_stable_ids_checksums_metadata_and_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "stable.txt"
    path.write_text("stable")
    source = connector(tmp_path, calculate_checksums=True)
    first = asyncio.run(all_items(source))[0]
    second = asyncio.run(all_items(source))[0]
    assert first.id == second.id
    assert first.checksum == second.checksum
    assert first.mime_type == "text/plain"
    assert first.modified_at is not None and first.modified_at.tzinfo is not None


def test_change_detection_add_modify_delete(tmp_path: Path) -> None:
    path = tmp_path / "change.txt"
    path.write_text("one")
    source = connector(tmp_path, calculate_checksums=True)
    initial = asyncio.run(source.detect_changes(None))
    assert initial.items[0].change_type is SourceChangeType.ADDED
    path.write_text("two changed")
    modified = asyncio.run(source.detect_changes(initial.next_cursor))
    assert modified.items[0].change_type is SourceChangeType.MODIFIED
    path.unlink()
    deleted = asyncio.run(source.detect_changes(modified.next_cursor))
    assert deleted.items[0].change_type is SourceChangeType.DELETED


def test_plain_text_parser_preserves_identity_newlines_and_languages(tmp_path: Path) -> None:
    path = tmp_path / "content.txt"
    path.write_bytes(b"Merhaba\r\nHello\rSon")
    source = connector(tmp_path)
    item = asyncio.run(all_items(source))[0]
    content = asyncio.run(source.get_content(item.id, 100))
    result = PlainTextParser(clock=lambda: NOW).parse(content)
    assert result.document.source.source_path == "content.txt"
    assert result.document.content == "Merhaba\r\nHello\rSon"
    assert result.document.normalized_content == "Merhaba\nHello\nSon"
    assert result.document.source.line_start == 1
    assert result.document.source.line_end == 3
    assert result.document.language is None
    assert result.metadata["chunked"] is False
    assert result.document.ingested_at == NOW


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Heading\nBody", "Heading"),
        ("---\ntitle: Front title\nauthor: synthetic\n---\n# Heading", "Front title"),
        ("Body without heading", "readme"),
    ],
)
def test_markdown_title_precedence(tmp_path: Path, text: str, expected: str) -> None:
    path = tmp_path / "readme.md"
    path.write_text(text)
    source = connector(tmp_path)
    item = asyncio.run(all_items(source))[0]
    result = MarkdownParser(clock=lambda: NOW).parse(asyncio.run(source.get_content(item.id, 1000)))
    assert result.document.title == expected
    assert result.document.content == text
    assert result.document.metadata["rendered"] is False


def test_markdown_headings_html_code_and_external_links_remain_untrusted(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    text = (
        "# Başlık\n## English\n<script>untrusted()</script>\n"
        "```python\nopen('must-not-exist', 'w')\n# not heading\n```\n"
        "[remote](https://example.invalid/resource)\n"
    )
    path = tmp_path / "unsafe.markdown"
    path.write_text(text)
    source = connector(tmp_path)
    item = asyncio.run(all_items(source))[0]
    result = MarkdownParser(clock=lambda: NOW).parse(asyncio.run(source.get_content(item.id, 5000)))
    headings = result.document.metadata["headings"]
    assert [(heading["level"], heading["text"]) for heading in headings] == [
        (1, "Başlık"),
        (2, "English"),
    ]
    assert "<script>" in result.document.content
    assert "https://example.invalid/resource" in result.document.content
    assert not marker.exists()
    assert result.metadata == {"chunked": False, "html_rendered": False, "links_fetched": False}


def test_connector_protocol_and_no_network_or_content_logging_dependencies(tmp_path: Path) -> None:
    source = connector(tmp_path)
    assert isinstance(source, SourceConnector)
    forbidden = {"httpx", "requests", "aiohttp", "socket", "logging", "structlog"}
    assert forbidden.isdisjoint(LocalFilesystemConnector.__init__.__globals__)
    assert forbidden.isdisjoint(MarkdownParser.__init__.__globals__)
