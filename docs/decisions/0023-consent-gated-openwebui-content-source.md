# ADR-0023: Consent-gated OpenWebUI content source

- **Status:** Accepted
- **Date:** 2026-07-14

## Context

Metadata discovery cannot support content security and quality checks. OpenWebUI knowledge files
must enter the same neutral pipeline as local files without introducing OpenWebUI types into Core or
silently transmitting credentials and content.

## Decision

Implement OpenWebUI as a read-only `SourceConnector`. A scan configuration stores only an approved
external credential reference; the first worker composition resolves `env:` references in memory.
Content retrieval requires explicit consent. Non-loopback endpoints require HTTPS, redirects and
environment proxies are disabled, responses and documents are bounded, pagination is cursor-based,
and upstream errors map to typed neutral source errors.

The connector reads selected knowledge metadata, enumerates knowledge-linked files, and retrieves
accessible file content through the upstream API. It does not mutate OpenWebUI, discover models,
scan chat endpoints, or claim incremental synchronization.

## Consequences

- OpenWebUI documents use the existing parsing, rule, scoring, history, and report pipeline.
- Core remains vendor-neutral and the remote access boundary is explicit in report provenance.
- Upstream API compatibility and change-detection policy remain open decisions.
- Standalone/chat-file selection, model/target roles, and other RAG platforms need separate adapters.
