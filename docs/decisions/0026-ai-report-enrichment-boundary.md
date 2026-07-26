# 0026: Keep optional AI report enrichment outside scanning Core

**Status:** Accepted

## Context

Users may want a local or API-hosted model to turn deterministic scan findings into a more detailed
advisory report. Core scanning must remain local-first and independent of model vendors.

## Decision

AI enrichment is an optional per-scan post-processing adapter. It receives a bounded, redacted
summary that excludes raw documents, validates structured output, and produces a new report
artefact. The evidence rules for structured analysis are refined by ADR-0045: bounded quality
evidence may be included, while raw static-security evidence is always omitted.
Ollama is loopback by default. Remote endpoints require explicit consent and HTTPS; credentials are
resolved only from `env:` references and are not persisted.

The supported catalog includes local Ollama, LM Studio, LocalAI, and vLLM plus OpenRouter, OpenAI,
NVIDIA NIM, Anthropic, Google Gemini, Groq, Mistral AI, Together AI, and custom OpenAI-compatible
endpoints. Provider/model/endpoint and credential references may be persisted in a job; secret
values may not. Remote analysis requires consent on that scan. Provider failure does not invalidate
or discard the deterministic report and is shown as a retryable advisory-analysis state.

## Consequences

Deterministic scan scores, findings, and history remain authoritative and unchanged. Embeddings,
AI-authored findings, and automatic remediation remain separate future work.
