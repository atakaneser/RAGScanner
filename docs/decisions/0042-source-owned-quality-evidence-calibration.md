# ADR-0042: Source-owned quality evidence calibration

**Status:** Accepted

**Supersedes:** The generated multi-chunk size-heuristic portion of ADR-0041. Plain evidence and
delivery escaping decisions remain unchanged.

## Context

Additional realistic variations exposed false positives beyond the initial OpenWebUI report. A
complete sentence without terminal punctuation was treated as a broken boundary. Short labels,
identifiers, code, and table cells made repetition ratios unstable. CJK body text was inferred to be
an uppercase heading because uncased letters compare equal in upper and lower forms. Generated
heading chunks, overlap, structural partitions, and full-document mirror chunks could also be
reported as source defects or duplicate a document-level finding.

## Decision

- Mark chunks created by RAGScanner explicitly and keep source/upstream chunk heuristics separate.
- Evaluate generated sentence boundaries only when the chunker records a forced split. Collapse one
  forced run to one structural finding and at most one start/end boundary pair.
- Apply size, near-limit, overlap, and excessive-count heuristics only to independently supplied
  upstream chunks. Keep explicit forced-structure findings for generated chunks.
- Require a 20-token sample for lexical repetition/density ratios and exclude heading-only, code,
  and table structure from those ratios.
- Consolidate overlapping extraction and content signals so one underlying defect does not create
  several equivalent findings.
- Require cased letters for inferred uppercase headings.
- Exclude generated heading-only and full-document mirror chunks from duplicate chunk scope. Balance
  near-duplicate containment by relative signature size.

## Consequences

Benign Markdown, short answers, punctuation variants, all six supported UI languages, CJK text,
tables, code, identifiers, and numeric answers no longer reduce report scores merely because of
scanner-owned structure or statistically weak samples. Real upstream fragmentation, sufficiently
large repetition, malformed extraction, forced structural splits, and material duplicate content
remain visible. Normalizer, chunker, exact/near duplicate, and chunk-quality versions advance;
regenerated chunk IDs and some finding fingerprints change. Existing saved reports remain immutable.
