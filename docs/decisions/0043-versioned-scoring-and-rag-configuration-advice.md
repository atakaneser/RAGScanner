# ADR-0043: Versioned scoring and workload-aware RAG configuration advice

**Status:** Accepted

## Context

The previous score implementation and documentation used different weights, did not retain a full
calculation snapshot, and could not explain missing dimensions. Chunk guidance also lacked a stated
workload, model limits, observed distribution, or retrieval-validation requirement. A single global
chunk-size recommendation would create false confidence.

## Decision

- Use a pure, configurable `ScoringPolicy` with a stable version, dimension weights, severity
  penalties, a critical-security cap, and minimum assessed-dimension coverage.
- Store the policy snapshot and calculation inputs in every report.
- Weight chunk-quality scores by token count and normalize the overall score only across dimensions
  that were actually assessed.
- Provide workload profiles as evidence-informed starting ranges, not automatic production tuning.
- Compare the selected profile with configured chunking, observed statistics, and declared model
  context limits.
- Always list the retrieval and answer metrics required to validate the recommendation.
- Keep calibration local and corpus-driven, with precision, recall, F1, uncertainty intervals, and
  language/format/rule slices.

## Consequences

Scores are reproducible and critical security findings cannot disappear in an average. Reports make
missing retrieval, answer, and freshness evidence explicit. Operators receive actionable chunk and
top-k candidates while retaining responsibility for representative-query evaluation. Existing saved
reports remain readable, but reports from different policy versions require a methodology warning
when compared. The bundled six-language corpus protects regression behavior but is not sufficient
for production accuracy claims.
