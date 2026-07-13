# ADR-0009: Versioned declarative rule packs with trusted execution

- Status: Proposed
- Date: 2026-07-12

## Context

RAGScanner requires evolving free rules, reproducible reports, and safe updates. Arbitrary downloadable code would expand the supply-chain attack surface.

## Decision

Define versioned rule metadata and a constrained declarative format where feasible; executable scanners ship as reviewed package code. Reports pin rule-pack and individual rule versions. Updates are integrity-checked, staged, reversible, publicly available, and never silently enable remote transmission. Treat rule content, regexes, URLs, and model prompts as untrusted inputs subject to resource limits.

## Consequences

Reproducibility and rollback improve. A schema, signing keys, compatibility, regex safety, and public distribution design are still required under OD-022.
