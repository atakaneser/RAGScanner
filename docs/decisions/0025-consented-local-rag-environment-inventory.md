# ADR-0025: Consented local RAG environment inventory

- **Status:** Accepted
- **Date:** 2026-07-15

## Context

Users should not need to know whether their local RAG knowledge is exposed through a container,
loopback service, vector store, or platform knowledge base before beginning a scan. At the same time,
container filesystem scraping, broad port scans, and automatic remote access would violate the
local-first consent boundary.

## Decision

Make consented local environment inventory the default guided CLI path and expose the same flow in
the localhost dashboard. Read only bounded running-container names, images, and published ports from
supported local runtime CLIs. Classify known OpenWebUI, Qdrant, Chroma, Weaviate, Milvus, and pgvector
image/name hints only when they expose an approved loopback port.

Probe OpenWebUI health only on its fixed approved loopback candidates. OpenWebUI is the sole current
platform with knowledge-base metadata and content connector support. All other platform results are
shown as detected-only, with no claims about collections, documents, content, or scan coverage.

The dashboard accepts only an external `env:` credential reference for OpenWebUI knowledge-base
discovery. It resolves the reference in local process memory; the value never enters browser fields,
SQLite, reports, or durable job payloads. A dashboard action may run one queued job only after the
job's existing explicit scan/content consent.

## Consequences

- A bare `ragscanner` command can find supported local OpenWebUI deployments without requesting a
  filesystem location.
- The dashboard can take a user from discovery to selected OpenWebUI job without copying IDs by hand.
- Generic vector platform detection remains honest and non-invasive until each connector has its own
  capability and security acceptance work.
- A long-running `ragscanner worker` remains preferable to the dashboard's one-job convenience action.
