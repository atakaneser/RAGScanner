# ADR-0019: Opt-in local history and forward-only migrations

- Status: Accepted
- Date: 2026-07-14

## Decision

Use SQLAlchemy Core behind a database-independent `ScanHistoryRepository` port and packaged Alembic
migrations for the first SQLite history implementation. Static scans remain non-persistent by
default. A user opts in with `--save-history` or an explicit `--history-db`; history commands use
the platform-native application data path defined by ADR-0024 unless `--database` is supplied.

The deterministic Core `scan.id` identifies equivalent scan configuration, not one execution.
Persistence therefore creates a separate opaque `history_id` for each distinct report snapshot.
Exact duplicate report snapshots are idempotent, while later executions with the same Core scan ID
remain separate history records.

No time-based deletion runs by default. Records remain until an explicit `history delete` operation
or future user-configured retention policy removes them. Schema upgrades are forward-only in normal
operation. Before upgrading an existing database whose revision differs from packaged head,
RAGScanner creates a restrictive-permission SQLite backup next to it. Automatic downgrade is not a
recovery strategy.

The database stores redacted, bounded report snapshots and normalized occurrence metadata. It
rejects credential-like values, uses transactions, foreign keys, WAL, a busy timeout, and `0600`
database permissions. A newly created parent directory uses `0700`.

## Rationale

Explicit persistence preserves the current local/offline scan behavior and avoids surprising disk
retention. A separate execution identity supports real history without changing Core fingerprint or
idempotency semantics. SQLAlchemy/Alembic preserve adapter boundaries and make schema state visible
from the first persistence revision.

## Consequences

- CLI history and coverage-aware comparison can operate before the API and dashboard exist.
- Users control whether scan evidence is retained locally and delete records explicitly.
- Migration backups consume disk space and are intentionally not deleted automatically.
- Configurable retention, artifact-directory storage, concurrency stress limits, and administrative
  recovery tooling remain later work.
