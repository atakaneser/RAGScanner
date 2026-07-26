# ADR-0041: Plain evidence and source-relative chunk sizing

**Status:** Accepted

## Context

Core scanners HTML-escaped finding evidence before it entered the report model. PDF escaped the
same value again for ReportLab markup, so source apostrophes such as `VPN'e` appeared literally as
`VPN&#x27;e`. The chunk-quality scanner also treated naturally short one-chunk documents as
undersized, compared unrelated document lengths as size outliers, and exposed approximate offsets
from ordinary normalization as source defects. An observed 24-document OpenWebUI report therefore
contained 13 low-severity findings that did not identify actionable source problems.

## Decision

- Store bounded and secret-masked finding evidence as plain source text in Core and report models.
- Decode semicolon-terminated HTML character references exactly once when they arrive through an
  OpenWebUI transport. Apply this after inert text extraction and before source offsets are
  calculated in every supported parser. Do not apply this compatibility normalization to local
  files, and do not recursively decode double-encoded input.
- Apply HTML, PDF-markup, spreadsheet-formula, and terminal handling only in the responsible delivery
  adapter. Untrusted evidence never becomes trusted markup.
- Emit undersized and extreme-size-outlier findings only for documents split into multiple chunks.
  Calculate the outlier baseline from chunks belonging to the same document.
- Keep approximate source mapping as provenance metadata and a chunking warning. Do not turn an
  offset approximation caused by lossless normalization into a source-content finding.

## Consequences

New reports display source punctuation faithfully while HTML remains escaped at interpolation and
PDF remains escaped before ReportLab parsing. Static-security and chunk-quality scanner versions
advance because evidence and finding fingerprints can change. Existing saved reports remain
immutable and can retain encoded evidence or superseded low-severity findings; users must rescan the
source to obtain the corrected assessment.

OpenWebUI compatibility normalization restores source characters such as `<`, `>`, `"`, and `'`
before deterministic analysis. Delivery adapters still escape that plain text independently, so an
HTML comment or tag cannot become executable or hide report markup.
