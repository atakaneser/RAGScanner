"""Bounded, non-rendering PDF text parser built on PyMuPDF."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from time import monotonic
from typing import Any

import pymupdf
from pydantic import BaseModel, Field

from ragscanner.domain import SourceContent
from ragscanner.domain.helpers import (
    REDACTED,
    contains_unreferenced_secret,
    mask_secret_like_values,
    normalize_control_characters,
    truncate_text,
)
from ragscanner.parsers.base import ParserResult, ParserWarning, build_document, normalize_newlines

PAGE_SEPARATOR = "\n<<<RAGSCANNER_PAGE_BOUNDARY:7F3D9A21>>>\n"
ESCAPED_PAGE_SEPARATOR = "<<<RAGSCANNER_PAGE_BOUNDARY_ESCAPED:7F3D9A21>>>"
_PDF_DATE = re.compile(r"^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})")


class PdfParserErrorCategory(StrEnum):
    UNSUPPORTED = "unsupported"
    INVALID_SIGNATURE = "invalid_signature"
    MALFORMED = "malformed"
    ZERO_PAGES = "zero_pages"
    ENCRYPTED = "encrypted"
    LIMIT_EXCEEDED = "limit_exceeded"
    TIMEOUT = "timeout"


class PdfParserError(Exception):
    def __init__(self, category: PdfParserErrorCategory, message: str, *, remediation: str) -> None:
        self.category = category
        self.remediation = mask_secret_like_values(remediation)
        super().__init__(mask_secret_like_values(message))

    def __repr__(self) -> str:
        return f"PdfParserError(category={self.category.value!r}, message={str(self)!r})"


class PdfParserConfig(BaseModel):
    maximum_file_size: int = Field(default=25 * 1024 * 1024, gt=0)
    maximum_page_count: int = Field(default=1_000, gt=0)
    maximum_extracted_characters: int = Field(default=5_000_000, gt=0)
    maximum_characters_per_page: int = Field(default=500_000, gt=0)
    maximum_metadata_field_length: int = Field(default=1_024, ge=64, le=16_384)
    timeout_seconds: float = Field(default=30, gt=0, le=600)


class PdfPageMetadata(BaseModel):
    page_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    separator_start: int | None = Field(default=None, ge=0)
    separator_end: int | None = Field(default=None, ge=0)
    character_count: int = Field(ge=0)
    empty: bool
    image_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class PdfExtractionStatistics(BaseModel):
    page_count: int = Field(ge=0)
    pages_with_text: int = Field(ge=0)
    empty_pages: int = Field(ge=0)
    total_characters: int = Field(ge=0)
    images_detected: int = Field(ge=0)
    warnings_count: int = Field(ge=0)


class PdfParser:
    name = "pdf"
    version = "1.0.0"

    def __init__(
        self,
        config: PdfParserConfig | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.config = config or PdfParserConfig()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic_clock or monotonic

    def parse(self, source: SourceContent) -> ParserResult:
        self._validate_source(source)
        self._validate_signature(source.content_bytes)
        if len(source.content_bytes) > self.config.maximum_file_size:
            raise PdfParserError(
                PdfParserErrorCategory.LIMIT_EXCEEDED,
                "PDF exceeds the configured file-size limit.",
                remediation="Increase the limit carefully or use a smaller PDF.",
            )
        started = self._monotonic()
        try:
            document = pymupdf.open(  # type: ignore[no-untyped-call]
                stream=source.content_bytes, filetype="pdf"
            )
        except (pymupdf.FileDataError, RuntimeError, ValueError) as error:
            raise PdfParserError(
                PdfParserErrorCategory.MALFORMED,
                "PDF is malformed, incomplete, or uses an unsupported structure.",
                remediation="Download the file again or export it as a valid PDF.",
            ) from error
        try:
            if document.needs_pass:
                raise PdfParserError(
                    PdfParserErrorCategory.ENCRYPTED,
                    "Password-protected PDF requires authentication.",
                    remediation="Create an authorized unencrypted copy and scan it again.",
                )
            page_count = self._page_count(document)
            if page_count > self.config.maximum_page_count:
                raise PdfParserError(
                    PdfParserErrorCategory.LIMIT_EXCEEDED,
                    "PDF exceeds the configured page-count limit.",
                    remediation="Increase the page limit carefully or split the document.",
                )
            warnings: list[ParserWarning] = []
            safe_metadata = self._metadata(document.metadata or {}, warnings)
            safe_metadata["page_count"] = page_count
            self._active_content_warnings(document, warnings)
            page_metadata: list[PdfPageMetadata] = []
            parts: list[str] = []
            offset = 0
            images_detected = 0
            pages_with_text = 0
            empty_pages = 0
            total_extracted_characters = 0
            nonempty_texts: list[str] = []
            for page_index in range(page_count):
                self._check_timeout(started)
                page_number = page_index + 1
                page_warning_codes: list[str] = []
                try:
                    page = document.load_page(page_index)  # type: ignore[no-untyped-call]
                    page_text = normalize_newlines(page.get_text("text", sort=True))
                except (RuntimeError, ValueError):
                    page_text = ""
                    self._warn(
                        warnings,
                        "extraction_failed_page",
                        "Text extraction failed for a PDF page.",
                        page_number,
                    )
                    page_warning_codes.append("extraction_failed_page")
                    page = None
                image_count = 0
                if page is not None:
                    try:
                        image_count = len(page.get_images(full=True))
                        self._page_action_warnings(document, page, warnings, page_number)
                    except (RuntimeError, ValueError):
                        self._warn(
                            warnings,
                            "page_resource_inspection_failed",
                            "Page resources could not be fully inspected.",
                            page_number,
                        )
                        page_warning_codes.append("page_resource_inspection_failed")
                images_detected += image_count
                if PAGE_SEPARATOR in page_text:
                    page_text = page_text.replace(PAGE_SEPARATOR, ESCAPED_PAGE_SEPARATOR)
                    self._warn(
                        warnings,
                        "page_separator_escaped",
                        "Extracted text contained the reserved page separator.",
                        page_number,
                    )
                    page_warning_codes.append("page_separator_escaped")
                if len(page_text) > self.config.maximum_characters_per_page:
                    raise PdfParserError(
                        PdfParserErrorCategory.LIMIT_EXCEEDED,
                        "A PDF page exceeds the extracted-character limit.",
                        remediation="Increase the character limit carefully or split the document.",
                    )
                separator_start: int | None = None
                separator_end: int | None = None
                if page_index:
                    separator_start = offset
                    parts.append(PAGE_SEPARATOR)
                    offset += len(PAGE_SEPARATOR)
                    separator_end = offset
                start_offset = offset
                parts.append(page_text)
                offset += len(page_text)
                total_extracted_characters += len(page_text)
                stripped = page_text.strip()
                if stripped:
                    pages_with_text += 1
                    nonempty_texts.append(stripped)
                else:
                    empty_pages += 1
                    self._warn(
                        warnings, "empty_page", "A PDF page has no extractable text.", page_number
                    )
                    page_warning_codes.append("empty_page")
                quality_codes = self._quality_warnings(page_text, warnings, page_number)
                page_warning_codes.extend(quality_codes)
                page_metadata.append(
                    PdfPageMetadata(
                        page_number=page_number,
                        start_offset=start_offset,
                        end_offset=offset,
                        separator_start=separator_start,
                        separator_end=separator_end,
                        character_count=len(page_text),
                        empty=not bool(stripped),
                        image_count=image_count,
                        warnings=sorted(set(page_warning_codes)),
                    )
                )
                if total_extracted_characters > self.config.maximum_extracted_characters:
                    raise PdfParserError(
                        PdfParserErrorCategory.LIMIT_EXCEEDED,
                        "PDF exceeds the total extracted-character limit.",
                        remediation="Increase the character limit carefully or split the document.",
                    )
            content = "".join(parts)
            self._document_quality_warnings(
                page_count,
                pages_with_text,
                empty_pages,
                images_detected,
                nonempty_texts,
                warnings,
            )
            self._check_timeout(started)
            statistics = PdfExtractionStatistics(
                page_count=page_count,
                pages_with_text=pages_with_text,
                empty_pages=empty_pages,
                total_characters=total_extracted_characters,
                images_detected=images_detected,
                warnings_count=len(warnings),
            )
            title = (
                safe_metadata.get("title")
                or PurePosixPath(source.item.path or source.item.name).stem
            )
            parsed_document = build_document(
                source,
                content=content,
                normalized_content=content,
                title=str(title),
                mime_type="application/pdf",
                metadata={
                    "pdf_metadata": safe_metadata,
                    "pages": [page.model_dump(mode="json") for page in page_metadata],
                    "page_separator": PAGE_SEPARATOR,
                    "page_offsets_include_separator": False,
                    "active_content_executed": False,
                    "attachments_extracted": False,
                },
                warnings=warnings,
                clock=self._now(),
            )
            return ParserResult(
                document=parsed_document,
                warnings=warnings,
                parser_name=self.name,
                parser_version=self.version,
                source_item_id=source.item.id,
                metadata={
                    "statistics": statistics.model_dump(mode="json"),
                    "chunked": False,
                    "ocr_used": False,
                    "active_content_executed": False,
                    "attachments_extracted": False,
                },
            )
        finally:
            document.close()  # type: ignore[no-untyped-call]

    def _validate_source(self, source: SourceContent) -> None:
        extension = PurePosixPath(source.item.path or source.item.name).suffix.casefold()
        if (
            source.content_type != "application/pdf"
            and source.item.mime_type != "application/pdf"
            and extension != ".pdf"
        ):
            raise PdfParserError(
                PdfParserErrorCategory.UNSUPPORTED,
                "PDF parser requires application/pdf content or a .pdf source.",
                remediation="Select the correct file or correct the source type.",
            )

    @staticmethod
    def _validate_signature(data: bytes) -> None:
        if data[:1024].find(b"%PDF-") < 0:
            raise PdfParserError(
                PdfParserErrorCategory.INVALID_SIGNATURE,
                "File does not contain a valid PDF signature.",
                remediation="Confirm that the file is a PDF and download it again.",
            )

    @staticmethod
    def _page_count(document: pymupdf.Document) -> int:
        try:
            page_count = int(document.page_count)
        except (pymupdf.FileDataError, RuntimeError, ValueError) as error:
            raise PdfParserError(
                PdfParserErrorCategory.MALFORMED,
                "PDF page information could not be read; the file may be malformed or incomplete.",
                remediation="Download the file again or export it as a valid PDF.",
            ) from error
        if page_count <= 0:
            raise PdfParserError(
                PdfParserErrorCategory.ZERO_PAGES,
                "PDF contains no scannable pages.",
                remediation="Use a valid PDF containing at least one page.",
            )
        return page_count

    def _metadata(self, metadata: dict[str, Any], warnings: list[ParserWarning]) -> dict[str, Any]:
        key_mapping = {
            "title": "title",
            "author": "author",
            "subject": "subject",
            "keywords": "keywords",
            "creator": "creator",
            "producer": "producer",
            "creationDate": "creation_date",
            "modDate": "modification_date",
        }
        safe: dict[str, Any] = {}
        for source_key, target_key in key_mapping.items():
            raw = metadata.get(source_key)
            if not raw:
                continue
            value = normalize_control_characters(str(raw))
            value = truncate_text(value, self.config.maximum_metadata_field_length)
            if contains_unreferenced_secret(value, parent_key=target_key):
                value = REDACTED
                self._warn(
                    warnings, "metadata_redacted", "A secret-like PDF metadata value was redacted."
                )
            else:
                value = mask_secret_like_values(value)
            if source_key in {"creationDate", "modDate"}:
                parsed = self._parse_pdf_date(value)
                if parsed is None:
                    self._warn(
                        warnings,
                        "malformed_metadata_date",
                        "A PDF metadata date could not be parsed.",
                    )
                else:
                    value = parsed
            safe[target_key] = value
        return safe

    @staticmethod
    def _parse_pdf_date(value: str) -> str | None:
        match = _PDF_DATE.match(value)
        if not match:
            return None
        try:
            year, month, day, hour, minute, second = (
                int(component) for component in match.groups()
            )
            parsed = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
        except ValueError:
            return None
        return parsed.isoformat()

    def _active_content_warnings(
        self, document: pymupdf.Document, warnings: list[ParserWarning]
    ) -> None:
        try:
            catalog = document.xref_object(  # type: ignore[no-untyped-call]
                document.pdf_catalog(),  # type: ignore[no-untyped-call]
                compressed=False,
            )
        except (RuntimeError, ValueError):
            self._warn(
                warnings,
                "active_content_inspection_failed",
                "PDF active-content catalog inspection failed.",
            )
            return
        if re.search(r"/(?:JavaScript|JS)\b", catalog):
            self._warn(
                warnings,
                "embedded_javascript",
                "PDF declares embedded JavaScript; it was not executed.",
            )
        if re.search(r"/(?:OpenAction|AA|Launch)\b", catalog):
            self._warn(
                warnings,
                "suspicious_action",
                "PDF declares an automatic or launch action; it was not executed.",
            )
        try:
            attachment_count = document.embfile_count()
        except (RuntimeError, ValueError):
            attachment_count = 0
            self._warn(
                warnings,
                "attachment_inspection_failed",
                "PDF attachment inventory could not be inspected.",
            )
        if attachment_count:
            self._warn(
                warnings, "embedded_files", "PDF contains embedded files; none were extracted."
            )

    def _page_action_warnings(
        self,
        document: pymupdf.Document,
        page: pymupdf.Page,
        warnings: list[ParserWarning],
        page_number: int,
    ) -> None:
        links = page.get_links()
        if links:
            self._warn(
                warnings,
                "embedded_links",
                "PDF page contains links; none were followed.",
                page_number,
            )
        if any(link.get("kind") == pymupdf.LINK_LAUNCH for link in links):
            self._warn(
                warnings,
                "launch_action",
                "PDF page contains a launch action; it was not executed.",
                page_number,
            )
        for annotation in page.annots() or ():  # type: ignore[no-untyped-call]
            try:
                raw = document.xref_object(  # type: ignore[no-untyped-call]
                    annotation.xref, compressed=False
                )
            except (RuntimeError, ValueError):
                continue
            if re.search(r"/(?:JavaScript|JS|Launch|OpenAction|AA)\b", raw):
                self._warn(
                    warnings,
                    "suspicious_action",
                    "PDF annotation contains an active action; it was not executed.",
                    page_number,
                )

    def _quality_warnings(
        self, text: str, warnings: list[ParserWarning], page_number: int
    ) -> list[str]:
        codes: list[str] = []
        if "\ufffd" in text:
            codes.append("replacement_characters")
        sample = text[: self.config.maximum_characters_per_page]
        if sample:
            controls = sum(
                not character.isprintable() and character not in "\n\r\t" for character in sample
            )
            printable = sum(character.isprintable() or character.isspace() for character in sample)
            whitespace = sum(character.isspace() for character in sample)
            lines = [line.strip() for line in sample.splitlines() if line.strip()]
            if controls / len(sample) > 0.02:
                codes.append("excessive_control_characters")
            if printable / len(sample) < 0.75:
                codes.append("low_printable_ratio")
            if whitespace / len(sample) > 0.65:
                codes.append("excessive_whitespace")
            if len(lines) >= 10 and sum(len(line) for line in lines) / len(lines) < 3:
                codes.append("fragmented_text")
            if re.search(r"(.{1,4})\1{5,}", sample):
                codes.append("repeated_garbled_sequence")
        for code in codes:
            self._warn(warnings, code, "Extracted PDF text has a quality warning.", page_number)
        return codes

    def _document_quality_warnings(
        self,
        page_count: int,
        pages_with_text: int,
        empty_pages: int,
        images: int,
        texts: list[str],
        warnings: list[ParserWarning],
    ) -> None:
        total_text = sum(len(text) for text in texts)
        if pages_with_text == 0:
            self._warn(warnings, "no_extractable_text", "PDF has no extractable text.")
            if images:
                self._warn(
                    warnings,
                    "likely_scanned_pdf",
                    "PDF is likely image-only or scanned; OCR was not performed.",
                )
        elif empty_pages and images:
            self._warn(
                warnings,
                "partially_scanned_pdf",
                "Some PDF pages may be scanned or image-only; OCR was not performed.",
            )
        elif images and total_text < max(20, page_count * 5):
            self._warn(
                warnings,
                "likely_scanned_pdf",
                "PDF has images and very little text; it may be scanned.",
            )
        if texts and all(re.fullmatch(r"(?:page\s*)?\d+", text, re.IGNORECASE) for text in texts):
            self._warn(
                warnings, "page_numbers_only", "PDF extraction returned only page-number-like text."
            )
        if (
            len(texts) > 1
            and len(set(text.casefold() for text in texts)) == 1
            and len(texts[0]) < 200
        ):
            self._warn(
                warnings,
                "repeated_boilerplate_only",
                "PDF extraction returned repeated short boilerplate text.",
            )

    def _check_timeout(self, started: float) -> None:
        if self._monotonic() - started >= self.config.timeout_seconds:
            raise PdfParserError(
                PdfParserErrorCategory.TIMEOUT,
                "PDF parsing exceeded the time limit.",
                remediation="Split the document or increase the time limit carefully.",
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("PDF parser clock must be timezone-aware")
        return value

    @staticmethod
    def _warn(
        warnings: list[ParserWarning], code: str, message: str, page_number: int | None = None
    ) -> None:
        warnings.append(
            ParserWarning(
                code=code,
                message=message,
                page_number=page_number,
                metadata={"page_number": page_number} if page_number is not None else {},
            )
        )
