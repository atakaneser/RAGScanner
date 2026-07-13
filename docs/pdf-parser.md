# PDF parser

The PyMuPDF parser supports text-based PDFs only. It opens bounded `SourceContent` memory, not file
paths or remote resources, and performs typed signature, page-count, zero-page, encryption, size,
page, text, metadata, and timeout checks. Raw library errors never cross the report boundary.

Pages are joined with a reserved ASCII separator and retain one-based page numbers, text/separator
offsets, character counts, image counts, empty flags, and warning codes. A page slice excludes the
separator, keeping future chunk-to-page mapping recoverable.

Warnings distinguish empty/no-text/likely-scanned/partially-scanned, page extraction failure,
replacement/control/printability/fragmentation/whitespace/garbling, page-number-only, and repeated
boilerplate signals. Image-only content is not malformed; it receives OCR-needed warnings. OCR is
not implemented.

Metadata is limited and control-normalized, secret-redacted, and bounded. JavaScript/actions, links,
embedded files, and annotations are inventoried as warnings only; nothing is executed, followed, or
extracted. There is no network or subprocess call. Timeout is cooperative between native calls, so
hostile-input process isolation remains future hardening. Complex layouts, fonts, damage, and scans
may yield incomplete text; the parser does not produce security findings.
