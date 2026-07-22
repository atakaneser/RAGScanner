# Architecture

## Selected shape

RAGScanner uses a Python modular monolith:

- Python 3.12+, framework-independent scanner Core, and Typer CLI
- Packaged FastAPI localhost API with public local history reads and scoped Bearer-authenticated
  asynchronous scan/job control
- Server-rendered Jinja2 dashboard with minimal vanilla JavaScript and CSRF-protected forms
- Opt-in SQLite history in WAL mode with packaged versioned migrations
- Durable SQLite job lifecycle, production static-scan handler, one-job worker process, and
  idempotent interval-schedule materialization
- One public monorepo, runnable locally or through a small Docker Compose topology (planned)

API and worker may be separate processes while sharing the same Python distribution, SQLite
database, and artifact directory. Redis, RabbitMQ, Celery, Kubernetes, PostgreSQL, Next.js,
organization models, and built-in auth are not first-release requirements.

The current composition keeps framework-independent use cases in `ragscanner.application`, FastAPI
delivery in `ragscanner.api`, dashboard delivery in `ragscanner.web`, and SQLite in
`ragscanner.storage`. `ragscanner serve` binds only to `127.0.0.1`; history reads are local while
scan creation and job control require a scoped Bearer key. It is not a remote or multi-user API.

## Repository boundaries

```text
apps/api       FastAPI composition and routes
apps/web       Jinja templates, HTMX, and static assets
apps/worker    job claiming, scheduling, and scan execution
packages/scanner        domain, orchestration, and ports
packages/connectors     filesystem, OpenWebUI, and future sources
packages/targets        active-test transports
packages/providers      optional analysis-model adapters
packages/security_rules versioned open rule content
packages/shared         configuration, storage adapters, and common schemas
```

The initial distribution may include several boundaries in one package. Directories express
dependency direction; separate packages require a real independent-release need.

```text
CLI / API / Web / Worker
          |
 application services
          |
 scanner domain + ports
    ^               ^
connectors/parsers  storage/model/report adapters
```

- Scanner Core imports no FastAPI, Typer, Jinja, SQLite, OpenWebUI, model-vendor, or MCP code.
- Rules depend on scanner rule contracts, not UI/storage.
- Connectors produce neutral source/document/chunk models.
- Targets transport active-test requests and do not evaluate vulnerabilities.
- Providers supply only optional scanner analysis models.
- `apps/*` composes services; the dashboard calls application services, never Core directly.
- `shared` contains no domain business rules.

## Storage

SQLite is selected for the first single-user/single-machine release. It stores knowledge bases,
non-secret connector configuration, schedules, scans, artifact references, documents, chunks,
findings, occurrences, status history, score snapshots, rule versions, and jobs. Raw content and
large artifacts remain in a content-addressed local directory.

Use WAL, busy timeout, short transactions, bounded retries, one active writer/worker, and batched
writes. Storage ports and SQLAlchemy/Alembic migrations keep a future PostgreSQL migration possible,
but PostgreSQL compatibility is not an initial test burden. Reconsider it only after measured write
contention, multiple workers, remote multi-user operation, or high-volume API deployment.

Secret values never enter domain models or SQLite as plain text; only environment/file/keychain-like
references are stored.

The current storage slices persist redacted report snapshots, normalized finding occurrences, and
durable job control metadata behind database-independent ports. A separate `history_id` identifies
an execution snapshot; the deterministic Core `scan.id` remains a configuration identity.
Persistence is opt-in, retention is explicit, and an older database is backed up before a forward
migration. Non-secret source profiles, dashboard preferences, and interval schedules are persisted.
Credential values stay outside SQLite in environment variables or owner-readable machine secret
files; durable records contain only opaque references. Document/chunk and artifact-reference tables
remain planned.

## Durable jobs

FastAPI in-process tasks are not durable enough for long scans. A `Job` table records queued work.
One worker atomically claims a lease, writes heartbeat/progress, checks cancellation, and finalizes
status. Expired leases may be reclaimed. Before each claim cycle, the worker materializes due
interval schedules as idempotent jobs. Scan effects use job/idempotency keys to prevent duplicate
findings.
The table, repository, production static-scan handler, CLI enqueue/control commands, authenticated
enqueue/control API, worker entry point, and interval-schedule materializer are implemented.

## Adapter contracts

- `SourceConnector`: descriptor/capabilities, health, paginated item/content reads, change detection,
  and typed source errors.
- `TargetAdapter`: authorized capability/health, request preparation/invocation, sessions, budgets,
  cancellation, and typed transport errors.
- `ModelProvider`: optional chat/embedding analysis with structured-output and locality/privacy
  metadata.

The same platform may implement multiple adapters, but configuration, credential references,
consent, and provenance remain separate. Unknown retrieval capability yields `llm` or
`unknown_retrieval`, and RAG-specific checks remain `not_assessed`.

Source implementations are capability-tiered rather than file-centric. They may expose raw
documents, precomputed chunks, metadata only, change feeds, deletion tombstones, retrieval traces,
or answer citations. SharePoint/OneDrive, bounded web/sitemap, SaaS knowledge, Git, object-store,
vector-store, OpenWebUI, and generic manifest/REST adapters map into the same neutral source models.
Core never imports their SDKs. Remote enumeration and content reads are separate consent boundaries,
and metadata-only access cannot silently claim content checks.

## Current static flow

```text
explicit local root
  -> root-confined discovery and bounded reads
  -> typed Markdown/TXT/PDF/DOCX and bounded ZIP-office/publication parsing
  -> versioned normalization and source mapping
  -> structure/paragraph/token-window chunking
  -> static security + exact/near duplicate + chunk-quality analysis
  -> assessed-only scores
  -> terminal / JSON / standalone escaped HTML
```

File-stage failures are isolated. Original content remains available for audit while normalized
content carries explicit provenance. Parsers do not render, execute, fetch, or perform OCR. PDF
parsing uses PyMuPDF first and a bounded pypdf text-only recovery pass only when the primary parser
cannot read page structure; recovery records its reduced active-content inspection coverage.
Reporting is framework-independent, applies final-boundary redaction, and performs no network access.

Default reports, history, jobs, source profiles, and local-administrator state share one
platform-native machine data root. The Host Service runtime is installed outside user profiles and
uses a service-owned temporary directory. Interactive disposable caches may use the signed-in
user's platform cache directory. CLI-supplied output/database paths and `RAGSCANNER_DATA_DIR` remain
explicit overrides for development and automation.

The platform supervisor is a `SYSTEM` boot task on Windows, a system `systemd` unit on Linux, and a
system `LaunchDaemon` on macOS. The Windows launcher is a console application, so it is deliberately
not registered directly with Service Control Manager; Task Scheduler provides boot execution and
restart-on-failure without requiring an interactive user session.

`ragscanner update` and `ragscanner repair` resolve the official GitHub `main` branch unless an
explicit `RAGSCANNER_INSTALL_SOURCE` override is configured. Windows installs each replacement into
a new machine-owned runtime generation, atomically updates the active-generation pointer, hands the
Task Scheduler definition to the new launcher, and only then attempts best-effort cleanup. This
avoids asking a running Windows executable to overwrite its own locked environment.

Windows also exposes a stable machine command under `%ProgramFiles%\RAGScanner\command`. Its command
dispatcher reads the active-generation pointer on every invocation. The installer owns the matching
machine `PATH` entry and removes it during uninstall, preventing a user-profile package bootstrap
from remaining the long-term command owner.

## Optional AI report flow

Each manual or durable scan may leave AI analysis off or select one local/remote provider. After the
deterministic report is built, the provider receives only a bounded, redacted summary of scores,
coverage, and up to 25 findings; it never receives raw documents or finding evidence. Structured
output is schema-validated and stored as an advisory section on the report. A model failure leaves
the deterministic report complete and records a retryable analysis-unavailable state. Remote
providers require HTTPS, an external credential reference, and explicit consent on that scan.
Common structured-output drift is normalized within the declared schema. References to findings
outside the bounded request are discarded and recorded rather than failing otherwise valid analysis.
Accepted output may attach advisory remediation and verification steps only to supplied findings.

## OpenWebUI content flow

After explicit configuration and consent, the OpenWebUI `SourceConnector` validates the endpoint,
enumerates a selected knowledge base through bounded pagination, retrieves bounded accessible file
content, and produces neutral source models for the same scanner pipeline. Core does not know
OpenWebUI API types. The worker resolves only an `env:` or protected machine-file credential reference.

The guided CLI separately checks consented container-runtime and common loopback health candidates
and can inventory authenticated KB/file metadata through per-knowledge-base file endpoints. A later
inventory failure does not discard an already successful KB result. Content access is a separate
explicit-consent job.

The CLI and dashboard share a consent-gated local environment inventory. It classifies bounded
running-container name, image, and published loopback-port metadata from Docker, Podman, nerdctl,
and Finch; bounded service metadata from the active Kubernetes context; and a fixed set of common
loopback health endpoints. Only OpenWebUI currently has a metadata/content source connector; all other
classifications remain detected-only hints and cannot imply RAG access or assessment coverage. The
dashboard resolves an external credential reference only in its local process to list OpenWebUI
knowledge bases, then persists only the reference in a consented job.

## Dashboard report flow

Guided and asynchronous scans persist a redacted `ReportDocument` snapshot in SQLite. The dashboard
renders overview, job, source, report archive, report detail, and coverage-aware comparison pages
from application services. Date/source filtering is performed by the history port. An authenticated
download route passes the persisted redacted snapshot to delivery-only HTML, XLSX, or PDF exporters;
these exporters do not import connectors, re-read raw documents, or perform network access. Explicit
CLI HTML/JSON exports remain separate delivery adapters.

Reports preserve file, page, and line provenance where parsers can supply it, plus a bounded matched
text fragment for safe highlighting. Security, knowledge quality, and efficiency feed the assessed-
dimension product score. Contradiction inference is not part of the pipeline; see ADR-0037.
HTML exports escape untrusted fields and prohibit scripts and connections through CSP. XLSX exports
neutralize formula-leading cells, and PDF uses embedded/local font resources with bounded report data.

## Active-security flow

```text
target-owner authorization
  -> safe versioned test selection
  -> TargetAdapter invocation under rate/timeout/request budget
  -> bounded and redacted observation
  -> deterministic evaluation and optional explicitly configured evaluator
  -> classified finding + coverage + transport status
```

Results distinguish `confirmed`, `probable`, `ambiguous`, and `not_detected`. Transport failure is
not a vulnerability. Destructive payloads are never default; safe tool tests use canary/no-op actions.

## Local topology

```text
browser -> FastAPI/Jinja :8000
CLI ----------|          |
              |       SQLite (WAL)
worker + scheduler ------|
              |
        local artifacts
```

The default bind is `127.0.0.1`. Any external exposure requires VPN/private network or
reverse-proxy authentication. OpenWebUI and user models remain external and optional.

## Security boundaries

- Filesystem roots, remote endpoints, parsers, decoded payloads, optional models, reports, and the
  browser are separate trust boundaries.
- File/page/object/decode/regex/response limits are mandatory.
- Suspicious commands and URLs are treated as text; they are never executed or fetched by default.
- Source/model content is escaped, redacted, and bounded before reports or templates.
- Remote document/model use is off by default and requires visible endpoint, consent, and provenance.
- Active tests require authorization and strict safe-mode controls.

## Failure behavior

- One parse failure does not abort a collection; coverage and remediation remain visible.
- Parser/resource failures do not permanently damage the worker.
- Database lock retries are bounded; exhaustion fails the job safely.
- Worker restart can reclaim an expired lease without duplicating idempotent effects.
- Cancellation preserves completed coverage at cooperative checkpoints.
- Unavailable connectors/models become failed checks; stale data is never presented as a new scan.
- Invalid rule/model output is rejected rather than converted into a vulnerability.
