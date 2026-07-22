# ADR-0040: Source-owned chunk-quality findings

**Status:** Accepted

## Context

Chunk-quality checks were evaluating artifacts created by RAGScanner's own structure-aware chunker
as if they were defects in the scanned source. Blank paragraph tails became empty chunks, Markdown
front-matter delimiters became punctuation-only chunks, a normal parent/child heading path was
classified as unrelated branches, and a fixed token overlap dominated short chunks. One observed
37-document OpenWebUI report reached the 500-finding display limit even though these signals did not
describe source-owned risks.

## Decision

- Attach whitespace and punctuation-only structural blocks to adjacent semantic content. A document
  containing only punctuation remains assessable instead of disappearing.
- Bound generated overlap by both the configured token maximum and 20 percent of the resulting
  chunk. The explicit overlap setting remains an upper bound, not a guaranteed amount.
- Treat `Chunk.headings` as an ancestry path. Do not infer unrelated sibling branches from multiple
  entries in that path.
- Exclude delimiter-only and front-matter-only chunks from cross-document exact-duplicate groups.
  Material repeated prose remains assessable.
- Group repeated rule occurrences in PDF delivery, show at most 20 locations per group, and direct
  users to HTML or Excel for the complete occurrence list. Persisted findings are not deleted.

## Consequences

Chunk and quality scanner versions advance to `1.1.0`; regenerated chunk identifiers change because
the configuration/version identity changes. Existing saved reports remain immutable and may still
contain older findings, but newly generated reports avoid these scanner-owned false positives.
PDF becomes a review summary while HTML and Excel remain exhaustive finding views.
