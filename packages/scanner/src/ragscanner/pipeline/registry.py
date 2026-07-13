"""Explicit deterministic parser registry; no dynamic imports or plugin execution."""

from pathlib import Path

from ragscanner.parsers import (
    DOCX_MIME,
    DocumentParser,
    DocxParser,
    DocxParserConfig,
    MarkdownParser,
    PdfParser,
    PdfParserConfig,
    PlainTextParser,
)


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
        registry.register(PlainTextParser(), content_types=("text/plain",), extensions=(".txt",))
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
        return registry
