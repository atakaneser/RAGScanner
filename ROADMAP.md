# Roadmap

Every milestone is free and open source.

## Milestone 0 — Product foundation

Product documentation, architecture, scanner/security model, issue backlog, monorepo layout,
Apache-2.0 licensing, and governance. **Status: complete.**

## Milestone 1 — Scanner Core

Python package, CLI, document/finding models, TXT/Markdown/PDF/DOCX ingestion, normalization,
chunking, persistence, and reports. **Status:** the offline ingestion → static security/quality →
scoring → terminal/JSON/HTML pipeline works. OCR and persistence are not implemented. Current work
focuses on English canonical documentation and usability hardening.

## Milestone 2 — RAG Security Scan

Static rules plus authorized active endpoint testing, versioned attack fixtures, target adapters,
deterministic response evaluation, operational limits, and safe reports. **Status:** static rules,
TargetAdapter contracts, safe test library, Generic REST transport, evaluator, in-memory runner, and
shared reports exist. Persistence and platform-specific adapters do not.

## Milestone 3 — RAG Health Scan

Exact/near/semantic duplicates, chunk quality, freshness, version conflicts, metadata quality,
Health Score, and RAG Rot. **Status:** exact and lexical near-duplicate plus chunk-quality analysis
exist. Semantic, freshness, conflict, metadata quality, and complete score formulas do not.

## Milestone 4 — BYOM and advanced analysis

Local embeddings, explicitly configured model providers, model diagnostics, balanced/deep modes,
contradiction verification, and answer faithfulness. **Status: not started.**

## Milestone 5 — Web dashboard

Overview, knowledge bases, scan history/detail/comparison, finding detail, schedules, connectors,
settings, and about. **Status: not started.**

## Milestone 6 — OpenWebUI and additional integrations

OpenWebUI synchronization and manual/scheduled scans plus prioritized source/target/model adapters.
**Status:** consent-based loopback health-candidate discovery exists; no content connector exists.

## Milestone 7 — Packaging and release

Docker/Compose, install automation, CI, package publishing, documentation website, and security
hardening. **Status:** baseline CI and GitHub installation work; no container or public release.
