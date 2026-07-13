# Document parsers

The parser port accepts `SourceContent` and returns a valid `Document` plus typed warnings, parser
name/version, source item ID, and metadata in `ParserResult`. Parsers do not discover/read files,
perform network calls, generate chunks, render content, or execute embedded instructions.

This release supports [plain text](text-parser.md), [Markdown](markdown-parser.md), text-based
[PDF](pdf-parser.md), and [DOCX](docx-parser.md). Legacy DOC, DOCM, HTML parsing, OCR, language
detection, and parser-level chunking are not available.

Original `Document.content` may be processed later by the separate
[document normalization pipeline](normalization.md). Minimal parser newline handling does not
replace that source-aware, versioned normalization result.
