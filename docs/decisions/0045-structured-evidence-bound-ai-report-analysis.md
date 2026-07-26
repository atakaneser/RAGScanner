# ADR-0045: Structured evidence-bound AI report analysis

**Status:** Accepted

## Context

Advisory model output could drift into partial schemas, contradict deterministic severity counts, or
hide incomplete scanner coverage. Duplicate interpretation also needs bounded source evidence to
distinguish template text, same-file indexing repetition, corpus skeletons, and version variants.
Sending raw documents would violate the local-first boundary.

## Decision

- Deterministic scanners remain the sole source of findings, severities, and scores.
- AI adapters receive at most 25 finding groups and ten secret-masked, truncated evidence rows per
  group, with file/page/line provenance and complete affected-chunk counts. They never receive a raw
  document.
- The version 2 prompt requires one exact JSON object containing analysis, evidence-bound root
  causes, ordered actions, review questions, score commentary, and a coverage caveat.
- Providers use temperature `0.1` and JSON mode when available. RAGScanner removes one optional JSON
  fence and retries invalid output once with an explicit JSON-only instruction.
- Local validation rejects severity framing that omits the supplied non-zero distribution and
  requires a caveat for every non-evaluated coverage area.
- A second invalid response records a localized advisory fallback. It never removes or changes
  deterministic report content.
- Enum values stay stable in storage and are translated only by display/export adapters.
- An accepted action attaches to a finding only when its `addresses` value equals that finding's
  deterministic rule ID.

## Consequences

AI interpretation has enough bounded evidence to explain duplicate patterns without expanding its
authority. Small local models may fail the stricter contract, but the retry and safe fallback make
that failure visible and leave a usable deterministic report. Adding or changing advisory fields
requires prompt, model, schema, export, and regression-test updates together.

## Links

- Extends [ADR-0026](0026-ai-report-enrichment-boundary.md).
- Duplicate comparison snapshots are defined by
  [ADR-0044](0044-bounded-duplicate-comparison-snapshots.md).
