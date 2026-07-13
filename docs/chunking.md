# Document chunking

The chunker accepts a `Document` and its hash-verified `NormalizationResult`. It mutates neither and
produces deterministic `Chunk` models. Chunking is not summarization, sanitization, duplicate
detection, or security scanning. It performs no rendering, execution, fetch, network, subprocess,
embedding, or LLM call.

Strategies are `structure_aware` (default), `paragraph_aware`, and `token_window`. Structure-aware
mode preserves heading paths, pages/sections, paragraphs, lists, tables, and code where possible.
Unrelated top-level heading branches, sections, and normally pages do not merge. A single oversized
block falls back to sentence then token boundaries and emits explicit forced/table/code/list split
warnings; content is never silently truncated.

Defaults target 300 approximate tokens, maximum 500, minimum 50, and overlap 30. Documents and
chunks also have explicit character/block/chunk/overlap limits. These are product defaults, not
scientific optima; complete configuration and algorithm/tokenizer versions enter provenance and
stable identity.

The tokenizer is a deterministic Unicode word/punctuation approximation, not model-specific BPE.
Overlap never exceeds maximum chunk size, does not cross page/section/top-level-heading boundaries,
and is reduced around tables/code to avoid full-block repetition.

Chunk IDs hash namespace/version, document ID, normalized hash, algorithm/tokenizer versions,
configuration identity, index, normalized range, and normalized content. Mapping preserves
normalized/original ranges, source path, lines, pages, sections, and parser blocks. Lossy mapping is
marked approximate. Exceeding the maximum chunk count returns a typed error rather than partial
lossy output.
