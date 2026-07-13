# ADR-0007: SQLite-backed single worker and APScheduler

- Status: Accepted
- Date: 2026-07-12

## Decision

Use one worker that claims/leases records from a SQLite `Job` table instead of FastAPI in-process
tasks. APScheduler only creates idempotent jobs for due schedules. RQ, Celery, and Dramatiq are not
used in the first release.

## Rationale

Long scans require restart recovery, progress, cancellation, and durable status. An additional
Redis/RabbitMQ service is unnecessary for the initial single-machine target.

## Consequences

Concurrency is bounded to one active writer/worker. If measured demand requires multiple workers,
the PostgreSQL/queue decision will be reopened. The worker is not implemented yet.
