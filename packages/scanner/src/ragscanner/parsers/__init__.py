"""Safe text document parser contracts and implementations."""

from ragscanner.parsers.base import DocumentParser, ParserResult, ParserWarning
from ragscanner.parsers.docx import (
    BLOCK_SEPARATOR,
    DOCX_MIME,
    DocxBlock,
    DocxBlockType,
    DocxParser,
    DocxParserConfig,
    DocxParserError,
    DocxParserErrorCategory,
)
from ragscanner.parsers.markdown import MarkdownParser
from ragscanner.parsers.pdf import (
    PAGE_SEPARATOR,
    PdfParser,
    PdfParserConfig,
    PdfParserError,
    PdfParserErrorCategory,
)
from ragscanner.parsers.text import PlainTextParser

__all__ = [
    "BLOCK_SEPARATOR",
    "DOCX_MIME",
    "PAGE_SEPARATOR",
    "DocumentParser",
    "DocxBlock",
    "DocxBlockType",
    "DocxParser",
    "DocxParserConfig",
    "DocxParserError",
    "DocxParserErrorCategory",
    "MarkdownParser",
    "ParserResult",
    "ParserWarning",
    "PdfParser",
    "PdfParserConfig",
    "PdfParserError",
    "PdfParserErrorCategory",
    "PlainTextParser",
]
