# ADR-0045: Structured evidence-bound AI report analysis

**Status:** Accepted

## Context

Advisory model output could drift into partial schemas, contradict deterministic severity counts, or
hide incomplete scanner coverage. Duplicate interpretation also needs bounded source evidence to
distinguish template text, same-file indexing repetition, corpus skeletons, and version variants.
Sending raw documents would violate the local-first boundary.

## Decision

- Deterministic scanners remain the sole source of findings, severities, and scores.
- AI adapters apply a global 18,000-character context budget. Finding groups are ordered by highest
  severity and then affected-chunk count; each selected group includes at most four secret-masked,
  truncated evidence rows with file/page/line provenance and complete affected-chunk counts. They
  never receive a raw document.
- Raw evidence is omitted for static-security findings and every other finding from the same
  affected source. Rule ID, provenance, impact, and deterministic recommendation remain available.
  This prevents detected document instructions from crossing into the advisory instruction plane.
- The version 2 prompt requires one exact JSON object containing analysis, evidence-bound root
  causes, ordered actions, review questions, score commentary, and a coverage caveat.
- Providers use temperature `0.1` and JSON mode when available. Ollama receives a 16,384-token
  context allocation. RAGScanner accepts one unambiguous
  analysis object from a JSON fence, reasoning prefix, serialized JSON string, or prose wrapper
  without repairing ambiguous JSON syntax.
- Invalid output is retried once with a separate recovery prompt, a context capped at 6,500
  characters, no evidence snippets, no provider JSON constraint, and bounded plain-text output.
  Requiring the same JSON behavior again made recovery depend on the capability that had already
  failed.
- Adapters normalize bounded, unambiguous shape variations from smaller local models. Verified
  severity distribution and non-evaluated coverage identifiers are added from deterministic report
  data when omitted; contradictory severity framing and missing core analysis text are still
  rejected.
- RAGScanner locally wraps usable plain text in a validated minimal `AIReportAnalysis`. It accepts no
  structured root causes or finding-bound actions from this path. Empty, malformed, wrong-language,
  or severity-contradicting text is replaced by a localized summary derived only from verified
  report facts. The limitation remains visible in the report instead of producing a terminal
  `ai_output_invalid`.
- Enum values stay stable in storage and are translated only by display/export adapters.
- An accepted action attaches to a finding only when its `addresses` value equals that finding's
  deterministic rule ID.

## Consequences

AI interpretation has enough prioritized bounded evidence to explain dominant patterns without
expanding its authority or overflowing ordinary local-model windows. Common local-model shape drift
does not discard otherwise useful analysis. A localized deterministic caveat identifies how many
lower-priority groups remain in the exhaustive report. JSON-incapable models can still return a
bounded minimal narrative, while unusable recovery text degrades to explicit verified facts rather
than an unavailable section. Adding or changing advisory fields requires prompt, model, schema,
export, and regression-test updates together.

## Links

- Extends [ADR-0026](0026-ai-report-enrichment-boundary.md).
- Duplicate comparison snapshots are defined by
  [ADR-0044](0044-bounded-duplicate-comparison-snapshots.md).
