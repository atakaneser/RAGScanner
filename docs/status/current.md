# Current status

**Milestone:** Milestones 1, 5, and 6 — scanner core plus initial local delivery and OpenWebUI source

**Version:** not released as a package or tag (`0.1.0a1` alpha candidate)

**Repository:** initial public baseline at `https://github.com/atakaneser/RAGScanner`

## Available now

- Python 3.12+ src-layout package locked with `uv`
- Typer CLI, Pydantic environment configuration, and structured logging
- Network-free `ragscanner doctor` and `ragscanner --version`
- One-command `ragscanner update`, `ragscanner repair`, and confirmed `ragscanner uninstall`, with
  deferred Windows removal that avoids self-locking executable-file failures
- Retired per-user Agent installation path; always-on delivery uses the machine service
- Elevated machine-local Host Service with an isolated machine runtime, machine-owned SQLite and
  temporary storage, a `local.ragscanner.com` loopback hosts-file mapping,
  a first-run local administrator, and an authenticated local dashboard bootstrap
- Windows Host supervision through a boot-triggered Task Scheduler task under `SYSTEM`, with
  restart-on-failure, explicit registration diagnostics, and no interactive-logon dependency
- One visible `ragscanner install` entry point that installs the complete machine service and opens
  the dashboard by default, with `--mode terminal` for CLI setup; legacy service groups are hidden
- English guided local scanning from a bare `ragscanner` command, bounded name-based RAG-folder
  discovery that excludes generic Documents/current-working-directory candidates,
  consent-based automatic Docker/Podman/nerdctl/Finch RAG-environment inventory, OpenWebUI endpoint
  discovery, and separately consented authenticated knowledge-base plus linked/standalone file
  metadata inventory with partial-result preservation and per-knowledge-base endpoint compatibility
- Platform-native central machine data, report, and history locations plus a separate per-user
  disposable cache location discoverable with
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
  local text-only pypdf recovery pass for PDFs whose page structure PyMuPDF cannot read and safe,
  classified diagnostics when both local readers reject a PDF
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
- Guided OpenWebUI selection and immediate one-knowledge-base content scan after separate explicit
  consent, using a process-memory-only API key and a central HTML report output
- Minimal guided menu with only local file/folder and direct OpenWebUI API scan routes
- Browser-tested local Jinja dashboard for scan posture, recent history, durable jobs, local and
  OpenWebUI enqueue, cancellation, retry, consented environment/knowledge-base discovery, and a
  one-job local worker action with same-origin CSRF protection
- Full local product navigation for Sources, Jobs, Reports, and Settings; remembered non-secret
  source profiles; date/source report filtering; report detail; and coverage-aware comparison
- Persistent browser-local language selection across setup, sign-in, navigation, jobs, sources,
  reports, settings, and dynamic status messages for English, Turkish, German, French, Simplified
  Chinese, and Italian; English remains the fallback
- Bounded Kubernetes service and common vector-platform localhost discovery in addition to
  Docker, Podman, nerdctl, and Finch metadata inventory
- Guided local and OpenWebUI scans persist reports for dashboard viewing instead of creating a
  standalone HTML file by default; explicit CLI export formats remain available
- HTML executive summary, assessment-coverage notice, and per-file ingestion remediation table
- Per-scan opt-in detailed-report enrichment for local Ollama, LM Studio, LocalAI, and vLLM or
  explicitly consented OpenRouter, OpenAI, NVIDIA NIM, Anthropic, Gemini, Groq, Mistral, Together,
  and custom endpoints; jobs persist only non-secret configuration and the provider receives only a
  bounded redacted finding summary. Validated advisory output is shown in dashboard/exports, while
  provider failure preserves the authoritative deterministic report
- Synthetic multilingual quickstart knowledge base and package/build smoke coverage
- pytest, Ruff, strict mypy, and GitHub Actions

## Not available yet

OCR, semantic duplicate analysis, freshness/version-conflict/metadata-quality analysis, complete
Health and RAG Rot formulas, semantic analysis beyond post-processing report enrichment, broader source connectors, incremental OpenWebUI
synchronization, remembered per-source content consent, filesystem watch, scheduler, configurable
retention, multi-user authentication, real LLM-assisted evaluation, and Docker deployment are not
implemented.

Qdrant, Chroma, Weaviate, Milvus, and pgvector containers can be detected from bounded local runtime
metadata but do not yet have inventory or content connectors. Detection is not an assessment.

Domain models do not perform scans and contain no network, filesystem, database, or UI access.

## Active delivery sequence

1. Complete persistence concurrency/recovery hardening and history/comparison filter/scale acceptance.
2. Define capability-tiered SharePoint, web/sitemap, SaaS knowledge, Git, object-store, vector-store,
   and generic RAG-environment connectors.
3. Add scheduling, retention, recurring jobs, and report-localization surfaces.
4. Resolve OpenWebUI compatibility, change detection, source identity, and broader secret providers.

## Next scoped issue

Proceed with the remaining `RS-016`, `RS-033`, and `RS-034` scale/recovery acceptance plus the
RS-056/063 heterogeneous-source capability matrix. Later work must not be presented as available
before its acceptance checks pass.

## Alpha release status

Apache-2.0 licensing, the canonical repository, and private GitHub Security Advisories are in place.
Final alpha package/tag verification remains separate work. See
[`docs/release-readiness-v0.1.0-alpha.1.md`](../release-readiness-v0.1.0-alpha.1.md).
