# ADR-0004: Explicit local-first provider and privacy policy

- Status: Proposed
- Date: 2026-07-12

## Context

Advanced analyses may benefit from customer models, but default remote transmission would violate product positioning and create privacy/security exposure.

## Decision

Default to offline deterministic execution. Configure chat and embedding providers independently through capability interfaces. Remote providers require explicit endpoint/model configuration and consent; ambient keys do not enable them. Run local candidate generation first, then redact and send only bounded relevant excerpts. Record provider/model, endpoint classification, remote-use flag, privacy policy, and skipped/failed checks in scan metadata. Never send raw documents to RAGScanner Cloud by default.

## Consequences

Users retain control and offline operation is testable. Some checks are unavailable without models and must appear as not assessed. Redaction is risk reduction, not a guarantee; the UX and terms must say so. Local model distribution and endpoint compatibility require explicit support matrices.

