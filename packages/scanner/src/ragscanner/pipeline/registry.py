"""Explicit deterministic parser registry; no dynamic imports or plugin execution."""

from pathlib import Path

from ragscanner.parsers import (
    DOCX_MIME,
    OFFICE_ARCHIVE_MIME_TYPES,
    DocumentParser,
    DocxParser,
    DocxParserConfig,
    MarkdownParser,
    OfficeArchiveParser,
    PdfParser,
    PdfParserConfig,
    PlainTextParser,
)

STRUCTURED_TEXT_MIME_TYPES = {
    ".txt": "text/plain",
    ".rst": "text/x-rst",
    ".adoc": "text/asciidoc",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".log": "text/plain",
}
SUPPORTED_DOCUMENT_EXTENSIONS = frozenset(
    {*STRUCTURED_TEXT_MIME_TYPES, ".md", ".markdown", ".pdf", ".docx", *OFFICE_ARCHIVE_MIME_TYPES}
)
DEFAULT_DOCUMENT_PATTERNS = tuple(
    f"*{extension}" for extension in sorted(SUPPORTED_DOCUMENT_EXTENSIONS)
)
DOCUMENT_MIME_TYPES = {
    **STRUCTURED_TEXT_MIME_TYPES,
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": DOCX_MIME,
    **OFFICE_ARCHIVE_MIME_TYPES,
}


class ParserRegistry:
    def __init__(self) -> None:
        self._mime: dict[str, DocumentParser] = {}
        self._extensions: dict[str, DocumentParser] = {}

    def register(
        self,
        parser: DocumentParser,
        *,
        content_types: tuple[str, ...],
        extensions: tuple[str, ...],
    ) -> None:
        for content_type in content_types:
            if content_type in self._mime:
                raise ValueError(f"parser already registered for {content_type}")
            self._mime[content_type] = parser
        for extension in extensions:
            normalized = extension.casefold()
            if normalized in self._extensions:
                raise ValueError(f"parser already registered for {normalized}")
            self._extensions[normalized] = parser

    def select(self, *, content_type: str | None, path: str | None) -> DocumentParser | None:
        if content_type and content_type in self._mime:
            return self._mime[content_type]
        extension = Path(path or "").suffix.casefold()
        return self._extensions.get(extension)

    @classmethod
    def defaults(
        cls,
        *,
        pdf_config: PdfParserConfig | None = None,
        docx_config: DocxParserConfig | None = None,
    ) -> "ParserRegistry":
        registry = cls()
        registry.register(
            PlainTextParser(),
            content_types=tuple(dict.fromkeys(STRUCTURED_TEXT_MIME_TYPES.values())),
            extensions=tuple(STRUCTURED_TEXT_MIME_TYPES),
        )
        registry.register(
            MarkdownParser(),
            content_types=("text/markdown",),
            extensions=(".md", ".markdown"),
        )
        registry.register(
            PdfParser(pdf_config), content_types=("application/pdf",), extensions=(".pdf",)
        )
        registry.register(
            DocxParser(docx_config), content_types=(DOCX_MIME,), extensions=(".docx",)
        )
        office = OfficeArchiveParser()
        registry.register(
            office,
            content_types=tuple(OFFICE_ARCHIVE_MIME_TYPES.values()),
            extensions=tuple(OFFICE_ARCHIVE_MIME_TYPES),
        )
        return registry
