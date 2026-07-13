# Current status

**Milestone:** Milestone 1 — scaffold, core domain, and static source contracts

**Version:** not released as a package or tag (`0.1.0a1` alpha candidate)

**Repository:** initial public baseline at `https://github.com/atakaneser/RAGScanner`

## Available now

- Python 3.12+ src-layout package locked with `uv`
- Typer CLI, Pydantic environment configuration, and structured logging
- Network-free `ragscanner doctor` and `ragscanner --version`
- One-command `ragscanner update`, `ragscanner repair`, and confirmed `ragscanner uninstall`
- English guided local scanning from a bare `ragscanner` command, bounded nearby-source discovery,
  and loopback OpenWebUI health-candidate checks only after explicit consent
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
- Bounded PDF and DOCX parsers with typed failure categories and remediation metadata
- Deterministic normalization, source mapping, and structure/paragraph/token-window chunking
- Versioned offline static security rules covering ten categories
- Exact and lexical near-duplicate analysis plus deterministic chunk-quality analysis
- Unified filesystem-to-report static pipeline with isolated file failures and assessed-only scoring
- Concise terminal summaries and versioned JSON/standalone HTML reports
- HTML executive summary, assessment-coverage notice, and per-file ingestion remediation table
- Synthetic multilingual quickstart knowledge base and package/build smoke coverage
- pytest, Ruff, strict mypy, and GitHub Actions

## Not available yet

OCR, semantic duplicate analysis, freshness/version-conflict/metadata-quality analysis, complete
Health and RAG Rot formulas, production OpenWebUI content integration, model providers,
persistence, API, dashboard, worker, scheduler, real LLM-assisted evaluation, and Docker deployment
are not implemented.

Domain models do not perform scans and contain no network, filesystem, database, or UI access.

## Active delivery sequence

1. Implement SQLite scan history and comparison on stable report contracts.
2. Add application services, a local API, and durable database-backed jobs.
3. Implement the consent-based OpenWebUI source connector.
4. Build the localhost dashboard against application services.

## Next scoped issue

Proceed to `RS-014 persistence schema` after RS-062 is reviewed and committed. Later work must not
be presented as available before its acceptance checks pass.

## Alpha release status

Apache-2.0 licensing, the canonical repository, and private GitHub Security Advisories are in place.
Final alpha package/tag verification remains separate work. See
[`docs/release-readiness-v0.1.0-alpha.1.md`](../release-readiness-v0.1.0-alpha.1.md).
