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
  characters, no evidence snippets, and a single required `ai_analysis` field. This keeps the schema
  instruction in small local-model context windows instead of repeating the original request.
- Adapters normalize bounded, unambiguous shape variations from smaller local models. Verified
  severity distribution and non-evaluated coverage identifiers are added from deterministic report
  data when omitted; contradictory severity framing and missing core analysis text are still
  rejected.
- A second invalid response records a localized advisory fallback. It never removes or changes
  deterministic report content.
- Enum values stay stable in storage and are translated only by display/export adapters.
- An accepted action attaches to a finding only when its `addresses` value equals that finding's
  deterministic rule ID.

## Consequences

AI interpretation has enough prioritized bounded evidence to explain dominant patterns without
expanding its authority or overflowing ordinary local-model windows. Common local-model shape drift
does not discard otherwise useful analysis. A localized deterministic caveat identifies how many
lower-priority groups remain in the exhaustive report. Irreparable output still triggers the compact
retry and reason-specific safe fallback, leaving a usable deterministic report. Adding or changing
advisory fields requires prompt, model, schema, export, and regression-test updates together.

## Links

- Extends [ADR-0026](0026-ai-report-enrichment-boundary.md).
- Duplicate comparison snapshots are defined by
  [ADR-0044](0044-bounded-duplicate-comparison-snapshots.md).
