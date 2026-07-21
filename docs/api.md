# Local application API

RAGScanner includes a technical-alpha localhost API for scan history and asynchronous static-scan
jobs. Start it with an API key kept outside the database:

```bash
export RAGSCANNER_API_KEY="replace-with-a-long-random-local-key"
ragscanner serve
```

Choose a shared history/job database when needed. The loopback port is fixed:

```bash
ragscanner serve --history-db ./private/history.sqlite3
```

The server always binds to `127.0.0.1:8765`. It is not a public or multi-user API. External bind
addresses, built-in accounts, sessions, RBAC, CORS, and reverse-proxy configuration are not
provided. Any exposure beyond localhost requires an independent trusted access boundary.

## Authentication and scopes

History reads remain loopback-local. Scan creation and job control require
`Authorization: Bearer $RAGSCANNER_API_KEY`. The environment-composed key grants these scopes:

- `scans:write`
- `jobs:read`
- `jobs:cancel`
- `jobs:retry`

Programmatic composition can register separate keys with narrower scopes. Keys are hashed in
memory, are never stored in SQLite, and are subject to an in-memory per-key rate limit of 60
requests per minute. Restarting the process resets authentication and rate-limit state.

## Endpoints

| Method | Path | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/health` | Local only | Process/API liveness and access mode |
| `GET` | `/api/v1/history` | Local only | Paginated execution history |
| `GET` | `/api/v1/history/{history_id}` | Local only | Persisted report detail |
| `GET` | `/api/v1/history/{baseline}/compare/{candidate}` | Local only | Coverage-aware comparison |
| `POST` | `/api/v1/scans` | `scans:write` | Queue a local file/folder scan |
| `POST` | `/api/v1/scans/openwebui` | `scans:write` | Queue a consented OpenWebUI knowledge scan |
| `GET` | `/api/v1/jobs` | `jobs:read` | Paginated durable jobs |
| `GET` | `/api/v1/jobs/{job_id}` | `jobs:read` | Durable job detail |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | `jobs:cancel` | Cancel queued or request running cancellation |
| `POST` | `/api/v1/jobs/{job_id}/retry` | `jobs:retry` | Requeue a failed or cancelled job |
| `GET` | `/openapi.json` | Local only | OpenAPI document with Bearer security schemes |
| `GET` | `/docs` | Local only | Interactive OpenAPI documentation |

History listing accepts bounded `limit` (1–200) and non-negative `offset` query parameters. It can
also filter by exact `source` name and inclusive `created_after` / `created_before` timestamps.
Timestamp filters must be ISO 8601 values with an explicit UTC offset, and the lower bound cannot be
later than the upper bound. Filtering and pagination are applied in SQLite before report payloads
are read.

Every scan-create request requires an `Idempotency-Key` header of 8–160 characters. Reusing a key
with the same payload returns the existing job; reusing it for different work returns a conflict.

```bash
curl -X POST http://localhost:8765/api/v1/scans \
  -H "Authorization: Bearer $RAGSCANNER_API_KEY" \
  -H "Idempotency-Key: manual-local-20260714-001" \
  -H "Content-Type: application/json" \
  -d '{"path":"/absolute/path/to/knowledge"}'
```

The API enqueues work; run `ragscanner worker` against the same data directory or database to
execute it.

## Errors and limits

Errors use a stable envelope:

```json
{"error":{"code":"authentication_required","message":"A valid Bearer API key is required."}}
```

Stable cases include invalid parameters, missing records, unavailable storage, invalid Host
headers, oversized declared bodies, missing authentication, insufficient scope, rate limiting, and
invalid job transitions. Responses set `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, and a no-referrer policy.
