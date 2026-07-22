# Current status

**Milestone:** Milestones 1, 5, and 6 — scanner core plus initial local delivery and OpenWebUI source

**Version:** not released as a package or tag (`0.1.0a1` alpha candidate)

**Repository:** initial public baseline at `https://github.com/atakaneser/RAGScanner`

## Available now

- Python 3.12+ src-layout package locked with `uv`
- Typer CLI, Pydantic environment configuration, and structured logging
- Network-free `ragscanner doctor` and `ragscanner --version`
- One-command `ragscanner update` and `ragscanner repair` pull the latest official GitHub `main`
  branch after the stable machine dispatcher is installed; Windows upgrades use atomic runtime
  generations so the running executable never overwrites its locked installation directory
- Stable Windows machine command registration dispatches new terminals to the active runtime
  generation instead of leaving the user-profile `uv` bootstrap as the long-term command owner
- Confirmed `ragscanner uninstall`, with deferred Windows removal that avoids self-locking
  executable-file failures
- Retired per-user Agent installation path; always-on delivery uses the machine service
- Elevated machine-local Host Service with an isolated machine runtime, machine-owned SQLite and
  temporary storage, a fixed `http://localhost:8765` address bound only to `127.0.0.1`,
  a first-run local administrator, authenticated password changes that rotate existing sessions,
  and an authenticated local dashboard bootstrap
- Windows Host supervision through a boot-triggered Task Scheduler task under `SYSTEM`, with
  restart-on-failure, explicit registration diagnostics, a LocalSystem SID principal,
  BOM-prefixed UTF-16LE task XML, and no interactive-logon dependency
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
- Concise task-oriented English root README plus structurally matched Turkish, German, French,
  Simplified Chinese, and Italian entry pages; advanced command details live in the canonical CLI guide
- Canonical English project documentation enforced by a regression test, with intentional
  multilingual scan fixtures kept separate
- Framework-independent source, document, chunk, finding, scan, score, active-test, and target
  contracts
- Vendor-neutral `SourceConnector` and `TargetAdapter` ports with deterministic test fakes
- Generic REST target adapter with declarative mapping and bounded transport safeguards
- Versioned active security test library, response evaluation, and in-memory active runner
- Root-confined filesystem connector for Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB,
  RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML, and log files
- Bounded PDF and DOCX parsers with typed failure categories and remediation metadata, including a
  local text-only pypdf recovery pass for PDFs whose page structure PyMuPDF cannot read and safe,
  classified diagnostics when both local readers reject a PDF
- Deterministic normalization, source mapping, and structure/paragraph/token-window chunking
- Versioned offline static security rules covering ten categories
- Exact and lexical near-duplicate analysis plus deterministic chunk-quality analysis
- False-positive controls for scanner-owned blank/delimiter chunks, Markdown front matter, normal
  heading ancestry, overlap capped at 20 percent of the generated chunk, naturally short
  single-chunk sources, cross-document size variation, and normalization-only approximate mappings
- Plain-text bounded finding evidence with output-context escaping, preserving apostrophes and
  quotation marks in dashboard and PDF views without weakening HTML safety
- Multilingual false-positive variation coverage for uncased scripts, headings, lists, tables, code,
  identifiers, numeric answers, small lexical samples, forced split runs, and upstream boundaries;
  generated full-document/heading chunks do not duplicate document-level findings
- Unified filesystem-to-report static pipeline with isolated file failures and assessed-only scoring
- Concise terminal summaries and versioned JSON/standalone HTML reports
- Authenticated saved-report downloads as localized standalone HTML, structured multi-sheet XLSX,
  and paginated PDF, generated locally from the persisted redacted report snapshot; PDF groups
  repeated rule occurrences while HTML/XLSX retain the exhaustive list
- Opt-in local SQLite report history with versioned migrations, execution identities, paginated CLI
  listing/detail/deletion, and coverage-aware comparison
- Framework-independent history application services and a versioned localhost API for history,
  detail, comparison, scoped Bearer-authenticated scan creation, and job control
- Bounded server-side history API pagination plus exact-source and explicit-offset timestamp
  filters, including large-result acceptance coverage
- Durable job contracts, SQLite queue migration, atomic lease/heartbeat, bounded retry and
  cancellation, production static-scan handler, CLI control surface, and worker process
- Consent-gated, read-only OpenWebUI knowledge-file content connector with bounded pagination,
  response limits, HTTPS outside loopback, and external `env:` credential resolution
- Consent-gated website connector for one page, supported documents, same-origin sitemaps, and
  accessible SharePoint URLs, with optional external bearer-token references and bounded one-time
  or recurring dashboard jobs
- Guided OpenWebUI selection and immediate one-knowledge-base content scan after separate explicit
  consent; dashboard-entered keys use protected owner-readable machine files while the terminal
  guided flow keeps its one-shot key only in process memory
- Minimal guided menu with only local file/folder and direct OpenWebUI API scan routes
- Browser-tested local Jinja dashboard for scan posture, recent history, durable jobs, local and
  OpenWebUI enqueue, cancellation, retry, consented environment/knowledge-base discovery, and a
  one-job local worker action with same-origin CSRF protection
- Full local product navigation for Sources, Jobs, Reports, and functional Settings; remembered non-secret
  source profiles; date/source report filtering; report detail; and coverage-aware comparison
- Separate one-time execution history and persistent interval schedules, with latest-report health,
  health-over-time visualization, readable public IDs, and safe job activity/error logs
- Editable interval schedules with an explicit next local run time and recurrence interval
- Assessed-dimension scoring across security, content quality, and efficiency; shared yellow/orange/red
  score bands, source page/line provenance, and bounded matched-evidence highlighting
- AI provider timeout increased from 45 to 180 seconds for slower local models; localized timeout
  guidance and selected-locale AI narratives across all six dashboard languages
- Persistent browser-local language selection across setup, sign-in, navigation, jobs, sources,
  reports, settings, and dynamic status messages for English, Turkish, German, French, Simplified
  Chinese, and Italian; English remains the fallback
- Secret-safe setup credential guidance in all dashboard languages, with persistent `env:` or
  owner-readable machine-file references, no submitted-value echo, and a connect-later state
- Direct dashboard API-key entry for OpenWebUI setup, source creation, inline scan-job connection,
  and default AI settings. Submitted keys are stored outside SQLite in owner-readable machine files;
  source profiles and durable jobs retain only opaque references, and the UI clearly distinguishes
  scan-ready connectors from metadata-only detected environments
- Simplified Sources and Scan jobs workflows with known-platform defaults, an explicit Custom
  option, selectable incomplete sources, connection testing, and knowledge-base loading in the
  same job drawer instead of a disabled `connection_required` dead end
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
- Live two-second dashboard job updates, AI-stage lease heartbeats and progress, complete detected
  model selection, update-safe machine credential files, and secret-safe success/failure activity codes
- Compatibility retry for Ollama and OpenAI-compatible HTTP 400 structured-output rejection, with
  an actionable `ai_provider_request_invalid` terminal error when compatibility mode also fails
- Tolerant schema normalization for advisory AI output, safe removal of invented finding references,
  and per-finding AI remediation plus verification steps
- CSRF-protected permanent report deletion; latest-health calculations use the latest remaining report
- Reference-led icon navigation with implemented-section shortcuts, automatic local-provider model
  inventory in Settings, stale configured-model removal, and safe source-secret reference repair after
  a machine-data path migration that preserved the protected secret file
- Stable `RAGSCN-`, `RAGREP-`, and `RAGSCH-` display identifiers, recurring interval schedules,
  source duplicate rejection, localized timestamps, detailed report navigation, and health history
- Synthetic multilingual quickstart knowledge base and package/build smoke coverage
- pytest, Ruff, strict mypy, and GitHub Actions

## Not available yet

OCR, semantic duplicate analysis, freshness/general semantic contradiction/superseded-version analysis,
complete Health and RAG Rot formulas, semantic analysis beyond post-processing report enrichment, authenticated
Microsoft Graph/SharePoint library discovery, broader source connectors, incremental OpenWebUI
synchronization, remembered per-source content consent, filesystem watch, cron/calendar schedules, configurable
retention, multi-user authentication, real LLM-assisted evaluation, and Docker deployment are not
implemented.

Qdrant, Chroma, Weaviate, Milvus, and pgvector containers can be detected from bounded local runtime
metadata but do not yet have inventory or content connectors. Detection is not an assessment.

Domain models do not perform scans and contain no network, filesystem, database, or UI access.

## Active delivery sequence

1. Complete persistence concurrency/recovery hardening and history/comparison filter/scale acceptance.
2. Define capability-tiered SharePoint, web/sitemap, SaaS knowledge, Git, object-store, vector-store,
   and generic RAG-environment connectors.
3. Extend interval scheduling with calendar rules, retention, and deeper report-content localization.
4. Resolve OpenWebUI compatibility, change detection, source identity, and broader secret providers.

## Next scoped issue

Proceed with the remaining `RS-016`, `RS-033`, and `RS-034` scale/recovery acceptance plus the
RS-056/063 heterogeneous-source capability matrix. Later work must not be presented as available
before its acceptance checks pass.

## Alpha release status

Apache-2.0 licensing, the canonical repository, and private GitHub Security Advisories are in place.
Final alpha package/tag verification remains separate work. See
[`docs/release-readiness-v0.1.0-alpha.1.md`](../release-readiness-v0.1.0-alpha.1.md).
