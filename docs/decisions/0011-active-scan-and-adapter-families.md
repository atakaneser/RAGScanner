# ADR-0011: Separate SourceConnector, TargetAdapter, and ModelProvider

- Status: Accepted
- Date: 2026-07-12

## Context

Filesystem, vector stores, OpenWebUI, OpenAI, and Hugging Face may provide one or more document
source, test target, or analysis-model roles. Combining them in one provider interface would blur
credentials, consent, and dependency boundaries.

## Decision

- `SourceConnector` reads documents, chunks, metadata, or knowledge-base content.
- `TargetAdapter` sends authorized black-box tests to a running RAG/LLM application.
- `ModelProvider` supplies an optional analysis model for RAGScanner itself.

Even when one platform fills multiple roles, each role has separate configuration, credential
references, consent, and provenance. An LLM endpoint is not proof of retrieval. OpenWebUI is an
adapter, not Core.

## Consequences

More contract fixtures are required, but Core remains vendor-neutral. Source access cannot silently
enable model use or active testing.
