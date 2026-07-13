# Document normalization

Normalization never changes `Document.content`. It returns deterministic normalized text, hashes,
source-mapping segments, annotations, warnings, statistics, and version in `NormalizationResult`.
It is not sanitization: suspicious instructions, URLs, code, and invisible Unicode remain auditable
as content or explicit markers. No render, execution, fetch, network, subprocess, or model call occurs.

Ordered stages normalize newlines and Unicode, mark controls/invisible characters, identify
protected structure, conservatively normalize whitespace, repair high-confidence PDF hyphen/wrap
cases, add structural annotations, detect repeated header/footer/page-number candidates, build source
mapping, enforce limits, and compute hashes/statistics.

NFC is default because it canonicalizes combining sequences without collapsing compatibility glyphs.
NFKC requires explicit configuration and records change counts. There is no transliteration;
multilingual text and emoji are preserved. NUL, bidi controls, zero-width, replacement, and soft
hyphen produce warnings/annotations and visible deterministic markers where safe. Emoji ZWJ remains
preserved.

Markdown code/tables/preformatted text, DOCX block separators, PDF page boundaries, headings, lists,
tables, sections, headers, and footers are handled conservatively. PDF line repair never crosses
page, heading, list, table, URL/path, or code boundaries. Every repair is counted and makes mapping
approximate. Boilerplate is annotated as a candidate and never removed by default.

Segments connect normalized ranges to original parsed ranges and source locations. Many-to-one,
repair, or bounded coalescing is marked approximate. Segment/annotation/output limits produce
warnings or typed errors; output is never silently truncated. Normalization does not generate
chunks, findings, duplicates, persistence records, or reports.
