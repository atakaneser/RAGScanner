# ADR-0005: Separate stable findings from scan occurrences

- Status: Proposed
- Date: 2026-07-12

## Context

Comparisons and workflows need to recognize an issue across scans even when evidence, severity, confidence, or locations shift. A scan-only finding row cannot represent durable lifecycle cleanly.

## Decision

Represent a stable `Finding` identity and scan-specific `FindingOccurrence`. Derive a versioned fingerprint from rule, stable source/document/location identities, and issue-specific canonical discriminators. Store evidence and observed severity/confidence on occurrences. Store status transitions as append-only history. Preserve fingerprint algorithm version and provide reconciliation when identity rules change.

Community serialized reports use the same conceptual contract. Its exact local persistence/history UX remains OD-003.

## Consequences

Comparison and audit become reliable and recurrence is explicit. Source identity quality becomes critical; connector changes can create apparent new issues. Migrations and fingerprint-version tests are required.

