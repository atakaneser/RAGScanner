# ADR-0010: SQLite-first storage

- Status: Accepted
- Date: 2026-07-12

## Decision

Store scan history, findings/occurrences, documents/chunks, schedules, connector configuration,
score snapshots, and job metadata in SQLite. Use WAL, busy timeout, short transactions, and versioned
migrations. Raw artifacts remain in the filesystem.

## Rationale

SQLite is the simplest reliable, zero-service option for a single-user/single-machine deployment.
PostgreSQL is not a proven first-release requirement.

## Migration

Storage ports remain database-independent and schema migrations are versioned. If multiple workers,
write contention, or remote multi-user deployment becomes measured demand, add a data-migration tool
and a new PostgreSQL ADR.
