# 0026: Keep optional AI report enrichment outside scanning Core

**Status:** Accepted

## Context

Users may want a local or API-hosted model to turn deterministic scan findings into a more detailed
advisory report. Core scanning must remain local-first and independent of model vendors.

## Decision

AI enrichment is a post-processing adapter. It receives a bounded, redacted summary that excludes
raw documents and finding evidence, validates structured output, and produces a new report artefact.
Ollama is loopback by default. Remote endpoints require explicit consent and HTTPS; credentials are
resolved only from `env:` references and are not persisted.

## Consequences

Deterministic scan scores, findings, and history remain authoritative and unchanged. Dashboard model
settings, embeddings, and additional provider adapters remain separate future work.
