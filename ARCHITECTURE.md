# Architecture

## Selected shape

RAGScanner uses a Python modular monolith:

- Python 3.12+, framework-independent scanner Core, and Typer CLI
- FastAPI application API (planned)
- Jinja2 + HTMX with minimal vanilla TypeScript for the dashboard (planned)
- SQLite in WAL mode with versioned migrations (planned)
- One database-backed worker with APScheduler enqueueing due schedules (planned)
- One public monorepo, runnable locally or through a small Docker Compose topology (planned)

API and worker may be separate processes while sharing the same Python distribution, SQLite
database, and artifact directory. Redis, RabbitMQ, Celery, Kubernetes, PostgreSQL, Next.js,
organization models, and built-in auth are not first-release requirements.

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

## Durable jobs

FastAPI in-process tasks are not durable enough for long scans. A `Job` table records queued work.
One worker atomically claims a lease, writes heartbeat/progress, checks cancellation, and finalizes
status. Expired leases may be reclaimed. APScheduler only creates idempotent jobs for due schedule
occurrences. Scan effects use job/idempotency keys to prevent duplicate findings.

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

## Current static flow

```text
explicit local root
  -> root-confined discovery and bounded reads
  -> typed TXT/Markdown/PDF/DOCX parsing
  -> versioned normalization and source mapping
  -> structure/paragraph/token-window chunking
  -> static security + exact/near duplicate + chunk-quality analysis
  -> assessed-only scores
  -> terminal / JSON / standalone escaped HTML
```

File-stage failures are isolated. Original content remains available for audit while normalized
content carries explicit provenance. Parsers do not render, execute, fetch, or perform OCR.
Reporting is framework-independent, applies final-boundary redaction, and performs no network access.

## Planned OpenWebUI flow

After explicit configuration and consent, an OpenWebUI SourceConnector will validate endpoint and
capability/version, synchronize a selected knowledge base through bounded pagination, and produce
neutral source models for the same scanner pipeline. Core will not know OpenWebUI API types.

The existing guided CLI checks only fixed loopback health candidates after consent. It does not read
content and is not the production connector.

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
