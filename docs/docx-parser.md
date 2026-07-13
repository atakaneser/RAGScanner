# DOCX parser

The DOCX parser processes `.docx`/DOCX MIME content from `SourceContent` entirely in memory without
rendering. It uses python-docx and preserves ordered paragraphs, tables, headings, list items,
section/page breaks, headers, and footers as blocks with combined-text offsets. Core properties are
bounded and secret-masked. Title precedence is core title → H1 → first visible body paragraph →
filename.

## Security model

- Preflight limits file size, ZIP entries, decompressed bytes, XML parts, and compression ratio.
- Unsafe paths and encrypted entries fail closed; XML is inspected with `defusedxml`.
- External relationships, templates, images, and links are bounded metadata only and never fetched.
- Macros, OLE/embedded objects, comments, tracked changes, and hidden text produce warnings; nothing
  is executed or extracted.
- No subprocess, shell, network, rendering, OCR, chunking, or scanner call occurs.

Legacy DOC, DOCM, OLE/encrypted, and malformed packages produce typed errors. Common heading/list
styles, table coordinates, merge signals, and repeated header rows are preserved where available.
Nested tables, visual page order, fields, drawings, text boxes, notes, comments, and pixel-perfect
layout are not guaranteed.

The parser is not a security scanner. Its visible text and structure feed later normalization,
chunking, and static security stages.
