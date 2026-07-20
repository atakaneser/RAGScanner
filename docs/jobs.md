# Durable jobs

RAGScanner packages a durable SQLite queue, a production static-scan job handler, CLI job control,
and a worker process. Local-file and explicitly consented OpenWebUI knowledge scans use the same
pipeline and report-history database.

## CLI workflow

```bash
ragscanner jobs enqueue-scan /absolute/path/to/knowledge
ragscanner jobs list
ragscanner jobs show JOB_ID
ragscanner worker
```

`ragscanner worker --once` claims at most one job and exits. A continuous worker polls until
interrupted. Use `--database` on enqueue and worker commands when they must share a non-default
database.

Queue an OpenWebUI scan without storing the credential value:

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui \
  --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID \
  --credential-ref env:OPENWEBUI_API_KEY \
  --consent-content
ragscanner worker
```

Cancel or retry work:

```bash
ragscanner jobs cancel JOB_ID
ragscanner jobs retry JOB_ID
```

## Lifecycle and recovery

- Enqueue is idempotent per job kind and key.
- A worker atomically claims a lease, renews heartbeat/progress, and checks cancellation at
  pipeline checkpoints.
- AI-enabled jobs expose separate deterministic-scan, provider-wait, validation, and report-save
  progress. The worker renews its lease every ten seconds while waiting for a provider.
- Queued cancellation is immediate; running cancellation is cooperative.
- Failed or cancelled work may be manually retried.
- Expired leases are reclaimed while attempts remain and safely failed at the attempt limit.
- Persisted failures are bounded and do not copy arbitrary exception text.

The dashboard polls durable state every two seconds and includes a Job activity log. Entries show
stable codes such as `source_path_not_found`, `source_permission_denied`, `ai_provider_timeout`,
`ai_provider_http_401`, and `ai_output_invalid` with bounded remediation-oriented messages. Raw
exceptions, provider response bodies, document content, and credentials are never logged.

Payloads are limited to 64 KiB. Plaintext credentials are rejected; only approved external
references such as `env:VARIABLE`, `keychain:ITEM`, `vault:PATH`, or `file-secret:PATH` may be
stored. The first packaged OpenWebUI worker resolver supports `env:` only.

SQLite uses WAL, foreign keys, a five-second busy timeout, restrictive file permissions, and short
transactions. One active worker is the supported alpha topology. Scheduling is not implemented.

See [ADR-0007](decisions/0007-background-execution.md),
[ADR-0021](decisions/0021-durable-job-lifecycle.md), and
[ADR-0022](decisions/0022-authenticated-local-job-control-and-dashboard.md).
