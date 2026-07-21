# ADR-0037: Remove labelled-value contradiction scoring

## Status

Accepted.

## Context

The bounded consistency scanner treated repeated `label: value` text as contradictory facts. In
procedural and multi-document corpora, labels did not provide enough subject or entity context to
distinguish real conflicts from unrelated values. Narrowing the heuristic reduced false positives
but also missed ordinary natural-language contradictions.

## Decision

Remove contradiction scanning, its assessment coverage, and its score dimension from new scans and
dashboard presentation. Keep report loading structurally tolerant so saved historical reports still
open. Version conflict and semantic contradiction coverage are explicitly `not_assessed`.

The overall product score is normalized across the remaining assessed security, knowledge-quality,
and efficiency dimensions. No AI narrative may silently become an authoritative contradiction
finding.

## Consequences

- New reports do not contain `consistency_conflict` findings or a consistency score.
- Historical report JSON remains readable, but the dashboard no longer presents the removed score.
- Contradiction analysis can return only through a future design with explicit entity grounding,
  evaluation data, and a documented accuracy threshold.
