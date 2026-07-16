# Changelog

## Unreleased

- Replace the duplicate discovery/content menu paths with a minimal local-file or direct OpenWebUI
  API scan menu, and close OpenWebUI clients on the same asyncio event loop that performed the scan.

- Let guided OpenWebUI option 3 select a discovered knowledge base and start a separately consented
  immediate local content scan, instead of ending after metadata inventory.

- Stop automatic RAG discovery from suggesting generic Documents folders or the current working
  directory; it now lists only immediate folders with RAG-oriented names as unverified candidates.

- Defer Windows `ragscanner uninstall` until its launcher exits, avoiding recurring locked-file
  access-denied failures from `uv tool uninstall`.

- Retry OpenWebUI knowledge-base metadata discovery once without pagination for compatible legacy
  or reverse-proxied installations, and show bounded redacted HTTP 400 diagnostics.
- Classify malformed-PDF reader failures without including untrusted parser text in reports.

- Added opt-in, validated AI report enrichment for local Ollama and explicitly consented HTTPS
  OpenAI-compatible endpoints. It transmits only bounded redacted finding summaries and writes a
  separate detailed JSON or HTML report without changing scan results or history.
- Added consent-gated automatic local RAG-environment discovery to the CLI and dashboard. It
  classifies known local container platform hints without reading content and keeps unsupported
  platforms explicitly detected-only.
- Added dashboard OpenWebUI URL/knowledge-base discovery through non-persisted `env:` credential
  references and a CSRF-protected action to process one already-consented queued job.
- Moved default RAGScanner data, guided HTML reports, and SQLite history into one platform-native
  per-user application directory, added `ragscanner paths`, and stopped guided reports from being
  written into the launch directory such as Windows System32.
- Added bounded pypdf text-only recovery when PyMuPDF cannot read a PDF's page structure.
- Made guided OpenWebUI discovery retain successful knowledge-base results when file inventory
  fails and use the supported per-knowledge-base file metadata endpoints without requesting content.
- Added durable static-scan jobs with idempotent enqueue, atomic leases, heartbeat, bounded retry,
  cooperative cancellation, a production handler, CLI job management, and `ragscanner worker`.
- Added a versioned localhost FastAPI with history reads and scoped Bearer-authenticated,
  rate-limited asynchronous local/OpenWebUI scan creation plus job read/cancel/retry routes.
- Added a browser-tested local Jinja dashboard with scan posture, recent scans, durable jobs,
  consented local/OpenWebUI enqueue, cancellation, retry, and CSRF protection.
- Added a consent-gated read-only OpenWebUI knowledge-file content connector with bounded
  pagination/content, typed errors, HTTPS outside loopback, and external credential references.
- Added opt-in SQLite scan history with SQLAlchemy/Alembic migrations, restrictive local
  permissions, pre-migration backups, immutable execution snapshots, CLI list/show/delete commands,
  and coverage-aware scan comparison.
- Added consent-based Docker, Podman, nerdctl/containerd, and Finch OpenWebUI endpoint discovery,
  plus bounded knowledge-base and linked/standalone file metadata inventory with an in-memory API
  key.
- Added report schema 1.1 ingestion issues, a concise terminal summary, and an HTML executive
  summary with partial-coverage and per-file remediation guidance.
- Established English as the canonical project and runtime language while retaining localized
  README entry points and multilingual scanner inputs; migrated canonical documentation and added a
  regression audit.
- Added CLI and filesystem tests for spaces, parentheses, Turkish, German, Arabic, Cyrillic, Chinese,
  emoji, and decomposed-Unicode filenames.
- Added shell-free `ragscanner update`, `ragscanner repair`, and confirmed `ragscanner uninstall`
  commands for uv-managed installations.
- Added English guided local scanning and consent-based OpenWebUI service-candidate discovery to the
  bare `ragscanner` command.
- PDF signature, zero-page, and PyMuPDF page-count failures now produce typed categories and
  remediation; one malformed file does not stop a collection scan.
- Documented a one-time `uv tool install` flow that does not require cloning the repository.
- Made the root README canonical English documentation and added Turkish, German, French,
  Simplified Chinese, and Italian localized README pages.

All notable project changes will be documented here. The project intends to follow Semantic Versioning once releasable artifacts exist and Keep a Changelog structure.

## [0.1.0-alpha.1] - Unreleased

### Added

- Milestone 0 product-foundation documentation, architecture decisions, roadmap, and implementation issue drafts.
- uv/Python src-layout scaffold, Typer CLI, Pydantic configuration/diagnostics, structured logging and CI.
- Framework-independent static/active/shared domain models with authorization, safety, fingerprinting, redaction and validation contracts.
- Deterministic offline terminal, versioned JSON and standalone HTML reporting with boundary redaction, filters and limits.
- Unified local static scan pipeline and `ragscanner scan` CLI with isolated file stages, assessed-only scoring, progress events, TOML configuration and atomic reports.
- Single-source and small multi-source knowledge bases with explicit assessment coverage.
- Alpha package metadata, bundled rules/schema, build verification and synthetic release assets.

No product version has been released.
