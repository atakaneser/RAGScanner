# ADR-0034: Machine secret files and interval schedules

## Status

Accepted; supersedes ADR-0033 for credentials entered directly in the dashboard.

## Context

Process-memory credentials disappeared whenever `ragscanner update`, repair, or a service restart
replaced the Host Service process. Recurring scans also require their referenced credentials to
remain resolvable without placing raw secret values in SQLite, job payloads, reports, or logs.

## Decision

The dashboard stores directly entered credentials in a machine data-directory `secrets/` folder.
The folder is owner-only and each file is owner-readable only on POSIX systems. SQLite stores an
opaque `file-secret:` reference; `env:` remains supported for externally managed deployments.
References are resolved only inside the Host Service and are never returned as secret values.

Recurring scan definitions are stored separately from job executions. A schedule contains a
validated non-secret job payload, an interval, enablement state, and next/last run timestamps. The
Host Service materializes each due occurrence into the existing durable queue with an idempotency
key, so every occurrence has its own job, log, readable ID, and immutable report.

Schedule creation may supply an explicit timezone-aware first-run timestamp selected in the
dashboard. The browser converts its local `datetime-local` value to UTC before submission. API or
legacy callers that omit the value retain the deterministic `creation time + interval` default.

## Consequences

- Updates and ordinary service restarts preserve dashboard-entered API credentials.
- If a machine-data migration preserves a protected secret file but changes the absolute data-root
  path encoded by an older reference, the dashboard may rebind only the validated secret basename
  inside the current `secrets/` directory and persist the repaired opaque reference.
- Database copies alone do not contain raw credentials, but machine secret files still require the
  same backup and access controls as other local credentials.
- This is protected filesystem storage, not application-level encryption or an OS keychain.
- Interval schedules are available now; cron/calendar expressions and filesystem watches remain
  separate future work.
