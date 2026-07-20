"""Bounded text extraction for ZIP-based office and publication documents."""

import re
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import PurePosixPath

from defusedxml import ElementTree

from ragscanner.domain import SourceContent
from ragscanner.parsers.base import ParserResult, build_document, normalize_newlines

OFFICE_ARCHIVE_MIME_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".epub": "application/epub+zip",
}
_MAX_ENTRIES = 5_000
_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
_NATURAL_NUMBER = re.compile(r"(\d+)")


class OfficeArchiveParser:
    """Extract inert text without rendering macros, formulas, links, or active content."""

    name = "office_archive"
    version = "1.0.0"

    def parse(self, source: SourceContent) -> ParserResult:
        suffix = PurePosixPath(source.item.path or "").suffix.casefold()
        if suffix not in OFFICE_ARCHIVE_MIME_TYPES:
            raise ValueError("office archive parser requires PPTX, XLSX, ODT, or EPUB")
        if len(source.content_bytes) > 25 * 1024 * 1024:
            raise ValueError("office archive exceeds the 25 MiB parser limit")
        try:
            with zipfile.ZipFile(BytesIO(source.content_bytes)) as archive:
                members = archive.infolist()
                if len(members) > _MAX_ENTRIES:
                    raise ValueError("office archive contains too many entries")
                total = sum(item.file_size for item in members)
                if total > _MAX_UNCOMPRESSED_BYTES or any(item.flag_bits & 0x1 for item in members):
                    raise ValueError("office archive is encrypted or exceeds extraction limits")
                selected = _selected_members(suffix, members)
                fragments = [_xml_text(archive.read(item)) for item in selected]
        except (ElementTree.ParseError, zipfile.BadZipFile) as error:
            raise ValueError("office archive is malformed") from error
        normalized = normalize_newlines("\n\n".join(item for item in fragments if item).strip())
        document = build_document(
            source,
            content=normalized,
            normalized_content=normalized,
            title=PurePosixPath(source.item.path or "").stem or None,
            mime_type=OFFICE_ARCHIVE_MIME_TYPES[suffix],
            metadata={"archive_entries_read": len(selected), "active_content_executed": False},
            warnings=[],
            clock=datetime.now(UTC),
        )
        return ParserResult(
            document=document,
            warnings=[],
            parser_name=self.name,
            parser_version=self.version,
            source_item_id=source.item.id,
            metadata={"chunked": False},
        )


def _selected_members(suffix: str, members: list[zipfile.ZipInfo]) -> list[zipfile.ZipInfo]:
    safe = [
        item
        for item in members
        if not item.is_dir()
        and not item.filename.startswith("/")
        and ".." not in PurePosixPath(item.filename).parts
    ]
    if suffix == ".pptx":
        selected = [
            item for item in safe if re.fullmatch(r"ppt/slides/slide\d+\.xml", item.filename)
        ]
    elif suffix == ".xlsx":
        selected = [
            item
            for item in safe
            if item.filename == "xl/sharedStrings.xml"
            or re.fullmatch(r"xl/worksheets/sheet\d+\.xml", item.filename)
        ]
    elif suffix == ".odt":
        selected = [item for item in safe if item.filename == "content.xml"]
    else:
        selected = [
            item
            for item in safe
            if PurePosixPath(item.filename).suffix.casefold() in {".xhtml", ".html", ".htm", ".xml"}
        ]
    return sorted(selected, key=lambda item: _natural_key(item.filename))[:1_000]


def _natural_key(value: str) -> list[str | int]:
    return [int(part) if part.isdigit() else part for part in _NATURAL_NUMBER.split(value)]


def _xml_text(payload: bytes) -> str:
    root = ElementTree.fromstring(payload)
    return " ".join(text.strip() for text in root.itertext() if text.strip())
