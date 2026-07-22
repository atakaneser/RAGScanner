# Chunk-quality scanner

`ChunkQualityScanner` evaluates existing chunks with deterministic offline heuristics. It neither
creates nor changes chunks and does not prove ideal retrieval quality, correctness, or semantic
consistency.

Checks cover empty/short/long/outlier chunks; structural split and source-mapping diagnostics;
assessable sentence-boundary damage; punctuation/number/page bias;
repetition and low information density; extraction/control-character signals; adjacent overlap;
near-identical neighbors; and excessive chunk counts.

Missing structural metadata is not treated as a definite failure. Findings are emitted only for
assessable signals, and thresholds remain configurable.

Scanner-owned structure is not reported as a source defect. Whitespace and Markdown/front-matter
delimiters stay attached to semantic content, generated overlap is capped at 20 percent of the
resulting chunk, and a parent/child heading ancestry path is not interpreted as unrelated branches.
Delimiter-only and front-matter-only chunks are also excluded from exact cross-document duplicate
groups while material repeated prose remains assessable.

A naturally short source that produces one complete chunk is not an undersized-chunk defect, and
documents of different legitimate lengths are not compared as chunk-size outliers. Size,
near-limit, neighbor-overlap, and chunk-count heuristics apply to upstream chunks rather than chunks
created by RAGScanner itself. Approximate source mapping remains an internal provenance warning
because ordinary lossless normalization can make offsets approximate; it is not reported as a
source-content finding.

Sentence-boundary checks require either upstream chunk boundaries or an explicit forced split. One
forced region produces one structural split finding and at most one start/end boundary pair instead
of a finding for every generated fragment. Lexical repetition and information-density ratios require
at least 20 tokens and do not evaluate heading-only, code, or table structure. CJK and other scripts
without letter case are not inferred to be uppercase headings.

Each chunk receives product-defined 0–100 dimensions for size, structure, density, overlap, source
mapping, and extraction, plus an overall heuristic score. This is not a model benchmark or industry
standard. Evidence is bounded, secret-masked, and stored as plain source text; each delivery adapter
escapes it for its own output context. Full chunks are not copied into reports.
The scanner performs no network, subprocess, rendering, embedding, or LLM call.
