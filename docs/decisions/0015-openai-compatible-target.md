# ADR-0015: OpenAI-compatible target support

- Status: Accepted
- Date: 2026-07-12

## Context

OpenAI, Hugging Face TGI, vLLM, LiteLLM, NIM, and other gateways expose similar chat protocols, but
their compatibility details differ.

## Decision

Implement an OpenAI-compatible TargetAdapter after Generic REST. Base URL, model, auth reference,
Chat Completions/Responses capability, streaming, and tool events are explicitly discovered or
configured. Ambient credentials never auto-enable an endpoint.

Compatibility does not prove that a target performs retrieval. Without verified retrieval, report
the target as `llm` or `unknown_retrieval` and keep RAG-specific tests not-assessed.

## Consequences

A shared protocol broadens platform access. Tier 1 support requires platform/version fixtures; a
compatibility marketing claim alone is insufficient.
