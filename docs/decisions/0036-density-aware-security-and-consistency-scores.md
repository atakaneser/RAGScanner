# ADR-0036: Density-aware security and consistency scores

## Status

Accepted.

## Context

A single arithmetic mean hid whether a report was weak because of security findings, conflicting
source facts, chunk quality, or redundant content. Reports also needed one stable color policy
across overview, archive, history bars, and detail views.

## Decision

RAGScanner reports security and explicit-fact consistency as separate assessed dimensions.
Consistency checking is deterministic and bounded: it compares repeated labelled facts and reports
distinct values without selecting a winner. It does not claim general semantic contradiction
coverage.

The overall product score is a normalized weighted average of assessed dimensions. Security starts
at weight 0.35, consistency at 0.30, knowledge quality at 0.20, and efficiency at 0.15. Security and
consistency receive a bounded density adjustment based on findings per processed document. Missing
dimensions are excluded instead of treated as zero.

The presentation band is healthy at 85 or above, yellow from 70 through 84.99, orange from 55
through 69.99, and red below 55. Color is accompanied by numeric text and is never the only signal.

## Consequences

- Security, consistency, and overall posture remain distinguishable.
- A dense concentration of security or contradiction findings has greater influence than isolated
  low-density findings.
- The score remains a versioned product metric, not a scientific guarantee.
- Semantic contradiction, freshness, and superseded-version inference remain separate future
  capabilities and are shown as partial or not assessed.
