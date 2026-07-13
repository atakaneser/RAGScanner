# Roadmap

Every milestone is free and open source.

## Milestone 0 — Product foundation

Product documentation, architecture, scanner/security model, issue backlog, monorepo layout,
Apache-2.0 licensing, and governance. **Status: complete.**

## Milestone 1 — Scanner Core

Python package, CLI, document/finding models, TXT/Markdown/PDF/DOCX ingestion, normalization,
chunking, persistence, and reports. **Status:** the offline ingestion → static security/quality →
scoring → terminal/JSON/HTML pipeline works. Opt-in SQLite report history, migration, CLI detail,
deletion, and comparison are implemented. The durable SQLite job lifecycle, production static-scan
handler, CLI control surface, and worker entry point are also implemented.
OCR, configurable retention, artifact storage, and API-scale history remain incomplete.

## Milestone 2 — RAG Security Scan

Static rules plus authorized active endpoint testing, versioned attack fixtures, target adapters,
deterministic response evaluation, operational limits, and safe reports. **Status:** static rules,
TargetAdapter contracts, safe test library, Generic REST transport, evaluator, in-memory runner, and
shared reports and initial local history exist. Durable active-runner persistence and
platform-specific adapters do not.

## Milestone 3 — RAG Health Scan

Exact/near/semantic duplicates, chunk quality, freshness, version conflicts, metadata quality,
Health Score, and RAG Rot. **Status:** exact and lexical near-duplicate plus chunk-quality analysis
exist. Semantic, freshness, conflict, metadata quality, and complete score formulas do not.

## Milestone 4 — BYOM and advanced analysis

Local embeddings, explicitly configured model providers, model diagnostics, balanced/deep modes,
contradiction verification, and answer faithfulness. **Status: not started.**

## Milestone 5 — Web dashboard

Overview, knowledge bases, scan history/detail/comparison, finding detail, schedules, connectors,
settings, and about. **Status:** framework-independent history/job services, localhost FastAPI,
authenticated mutation, and an initial browser-tested overview/queue dashboard exist. Scan detail,
comparison, schedules, connector settings, and accessibility-matrix acceptance remain incomplete.

## Milestone 6 — Heterogeneous RAG sources and environments

OpenWebUI synchronization and manual/scheduled scans plus capability-tiered source, target, and
model adapters. Planned source families include SharePoint/OneDrive, bounded websites and sitemaps,
Confluence/Notion-like knowledge services, Git repositories, object stores, OpenAI vector stores,
Qdrant, Chroma, Weaviate, Pinecone, Milvus, pgvector, and generic manifests or REST exports. Unknown
RAG applications use vendor-neutral contracts rather than provider branches in Core. **Status:**
container/loopback OpenWebUI discovery, authenticated KB/file metadata inventory, and a
consent-gated read-only knowledge-file content connector exist. Incremental synchronization and all
other source families remain incomplete.

## Milestone 7 — Packaging and release

Docker/Compose, install automation, CI, package publishing, documentation website, and security
hardening. **Status:** baseline CI and GitHub installation work; no container or public release.
