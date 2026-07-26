# Duplicate detection

RAGScanner provides two deterministic offline duplicate views. Neither service changes or deletes
documents/chunks or uses network, models, or embeddings.

## Exact duplicates

`ExactDuplicateScanner` groups normalized document and chunk content by SHA-256 in separate scopes.
Empty content is not a duplicate. Repeated chunks within a document, identical chunks across
documents, and identical normalized documents are distinct categories. Each group has a stable
canonical reporting reference—not an automatic keep/delete decision—and bounded redacted evidence
plus estimated redundant characters/tokens.

Duplicate chunk candidates must contain at least 48 characters and six tokens by default. This
materiality gate suppresses isolated classification labels, punctuation fragments, and short
headings that consume negligible retrieval capacity. It does not apply to complete-document
duplicate analysis and is configurable through `DuplicateScanConfig`.

RAGScanner-generated heading-only chunks are structural context, not duplicate content. A generated
chunk that mirrors its complete normalized document is also excluded from chunk scope so one pair of
identical single-chunk documents produces one document finding rather than duplicate document and
chunk findings.

## Near duplicates

`NearDuplicateScanner` creates fixed-size Unicode token shingles and evaluates Jaccard plus
size-balanced containment
within bounded candidate buckets. Defaults are 0.82 similarity, five-token shingles, and 120 minimum
characters. Exact matches remain owned by the exact scanner.

Boilerplate/page-number annotations may be removed from the comparison signature but never from
source content. Because lexical similarity does not prove semantic equivalence, findings are
`probable` and require review. Multilingual text is supported without stemming or semantic analysis.
Size balancing prevents a common subsection contained in a much longer document from being treated
as if both complete documents were near duplicates.

Report schema 1.5 preserves each retained member's basename, page, line range, and bounded redacted
excerpt. Reports present the reference and matching occurrences together. Exact groups highlight
the compared excerpts; near groups also show bounded common phrases. Older report snapshots remain
readable but require a rerun to populate these comparison details.

Document, chunk, group, finding, shingle, bucket, comparison, evidence, and runtime limits produce
typed warnings and visible skipped IDs. Identical input, configuration, and scanner version produce
identical ordering, groups, fingerprints, statistics, and warnings.

```bash
ragscanner quality scan ./knowledge --format json
ragscanner quality scan ./knowledge --similarity-threshold 0.9 --fail-on medium
```
