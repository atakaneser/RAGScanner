# Chunk-quality scanner

`ChunkQualityScanner` evaluates existing chunks with deterministic offline heuristics. It neither
creates nor changes chunks and does not prove ideal retrieval quality, correctness, or semantic
consistency.

Checks cover empty/short/long/outlier chunks; structural split and approximate-mapping warnings;
missing heading context; sentence-boundary damage; punctuation/number/page bias;
repetition and low information density; extraction/control-character signals; adjacent overlap;
near-identical neighbors; and excessive chunk counts.

Missing structural metadata is not treated as a definite failure. Findings are emitted only for
assessable signals, and thresholds remain configurable.

Scanner-owned structure is not reported as a source defect. Whitespace and Markdown/front-matter
delimiters stay attached to semantic content, generated overlap is capped at 20 percent of the
resulting chunk, and a parent/child heading ancestry path is not interpreted as unrelated branches.
Delimiter-only and front-matter-only chunks are also excluded from exact cross-document duplicate
groups while material repeated prose remains assessable.

Each chunk receives product-defined 0–100 dimensions for size, structure, density, overlap, source
mapping, and extraction, plus an overall heuristic score. This is not a model benchmark or industry
standard. Evidence is bounded, escaped, and secret-masked; full chunks are not copied into reports.
The scanner performs no network, subprocess, rendering, embedding, or LLM call.
