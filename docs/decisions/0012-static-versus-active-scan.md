# ADR-0012: Separate static and active black-box scans

- Status: Accepted
- Date: 2026-07-12

## Context

Finding malicious instructions in documents and observing a running application's response require
different data, authorization, and evidence models.

## Decision

`static` mode analyzes only SourceConnector documents/chunks/metadata. `active` mode sends authorized
tests only through TargetAdapter. Provenance records coverage for each mode separately; one mode
never fills the other's coverage.

An endpoint is a RAG target only when retrieval is verified through capabilities or fixtures. Using
OpenAI, Hugging Face, or another LLM does not prove RAG behavior.

## Consequences

Static findings link to source locations; active findings link to test/request/response evidence.
They share a Finding contract while occurrences and coverage remain mode-specific.
