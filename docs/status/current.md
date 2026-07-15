# Current status

**Milestone:** Milestones 1, 5, and 6 — scanner core plus initial local delivery and OpenWebUI source

**Version:** not released as a package or tag (`0.1.0a1` alpha candidate)

**Repository:** initial public baseline at `https://github.com/atakaneser/RAGScanner`

## Available now

- Python 3.12+ src-layout package locked with `uv`
- Typer CLI, Pydantic environment configuration, and structured logging
- Network-free `ragscanner doctor` and `ragscanner --version`
- One-command `ragscanner update`, `ragscanner repair`, and confirmed `ragscanner uninstall`
- English guided local scanning from a bare `ragscanner` command, bounded nearby-source discovery,
  consent-based automatic Docker/Podman/nerdctl/Finch RAG-environment inventory, OpenWebUI endpoint
  discovery, and separately consented authenticated knowledge-base plus linked/standalone file
  metadata inventory with partial-result preservation and per-knowledge-base endpoint compatibility
- Platform-native central per-user data, report, and history locations discoverable with
  `ragscanner paths`; guided reports never default to the current working directory
- Canonical English root README plus Turkish, German, French, Simplified Chinese, and Italian
  localized README pages
- Canonical English project documentation enforced by a regression test, with intentional
  multilingual scan fixtures kept separate
- Framework-independent source, document, chunk, finding, scan, score, active-test, and target
  contracts
- Vendor-neutral `SourceConnector` and `TargetAdapter` ports with deterministic test fakes
- Generic REST target adapter with declarative mapping and bounded transport safeguards
- Versioned active security test library, response evaluation, and in-memory active runner
- Root-confined filesystem connector for TXT, Markdown, PDF, and DOCX
- Bounded PDF and DOCX parsers with typed failure categories and remediation metadata, including a
  local text-only pypdf recovery pass for PDFs whose page structure PyMuPDF cannot read
- Deterministic normalization, source mapping, and structure/paragraph/token-window chunking
- Versioned offline static security rules covering ten categories
- Exact and lexical near-duplicate analysis plus deterministic chunk-quality analysis
- Unified filesystem-to-report static pipeline with isolated file failures and assessed-only scoring
- Concise terminal summaries and versioned JSON/standalone HTML reports
- Opt-in local SQLite report history with versioned migrations, execution identities, paginated CLI
  listing/detail/deletion, and coverage-aware comparison
- Framework-independent history application services and a versioned localhost API for history,
  detail, comparison, scoped Bearer-authenticated scan creation, and job control
- Durable job contracts, SQLite queue migration, atomic lease/heartbeat, bounded retry and
  cancellation, production static-scan handler, CLI control surface, and worker process
- Consent-gated, read-only OpenWebUI knowledge-file content connector with bounded pagination,
  response limits, HTTPS outside loopback, and external `env:` credential resolution
- Browser-tested local Jinja dashboard for scan posture, recent history, durable jobs, local and
  OpenWebUI enqueue, cancellation, retry, consented environment/knowledge-base discovery, and a
  one-job local worker action with same-origin CSRF protection
- HTML executive summary, assessment-coverage notice, and per-file ingestion remediation table
- Synthetic multilingual quickstart knowledge base and package/build smoke coverage
- pytest, Ruff, strict mypy, and GitHub Actions

## Not available yet

OCR, semantic duplicate analysis, freshness/version-conflict/metadata-quality analysis, complete
Health and RAG Rot formulas, semantic analysis, broader source connectors, incremental OpenWebUI
synchronization, model providers, scheduler, configurable retention, dashboard scan detail and
comparison, multi-user authentication, real LLM-assisted evaluation, and Docker deployment are not
implemented.

Qdrant, Chroma, Weaviate, Milvus, and pgvector containers can be detected from bounded local runtime
metadata but do not yet have inventory or content connectors. Detection is not an assessment.

Domain models do not perform scans and contain no network, filesystem, database, or UI access.

## Active delivery sequence

1. Complete persistence concurrency/recovery hardening and history/comparison filter/scale acceptance.
2. Define capability-tiered SharePoint, web/sitemap, SaaS knowledge, Git, object-store, vector-store,
   and generic RAG-environment connectors.
3. Add scheduling, retention, and dashboard scan detail/comparison/settings surfaces.
4. Resolve OpenWebUI compatibility, change detection, source identity, and broader secret providers.

## Next scoped issue

Proceed with the remaining `RS-016`, `RS-033`, and `RS-034` scale/recovery acceptance plus the
RS-056/063 heterogeneous-source capability matrix. Later work must not be presented as available
before its acceptance checks pass.

## Alpha release status

Apache-2.0 licensing, the canonical repository, and private GitHub Security Advisories are in place.
Final alpha package/tag verification remains separate work. See
[`docs/release-readiness-v0.1.0-alpha.1.md`](../release-readiness-v0.1.0-alpha.1.md).
