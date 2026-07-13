# ADR-0006: Version scores and disclose coverage

- Status: Proposed
- Date: 2026-07-12

## Context

Health and RAG Rot scores aid prioritization but can create false confidence, especially when source capabilities or model checks are absent.

## Decision

Treat both as configurable, versioned product metrics. Persist category inputs, policy version, weights/caps, coverage, unavailable/failed/skipped checks, and explanations alongside results. Never infer a perfect category from zero evidence. Permit critical security caps through visible policy. Market neither score as scientific truth.

## Consequences

Historical comparison must account for policy-version changes, and UI/report design needs not-assessed states. Calibration work delays a simplistic score but prevents misleading labels. Exact formulas remain OD-005 and OD-006.

