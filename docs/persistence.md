# Local scan history and comparison

RAGScanner can optionally persist redacted report snapshots to local SQLite. Ordinary scans do not
create a database unless persistence is explicitly requested.

## Save a scan

Use the default `.ragscanner/history.sqlite3` location:

```bash
ragscanner scan ./knowledge-base --save-history
```

Or select an explicit database:

```bash
ragscanner scan ./knowledge-base --history-db ./private/history.sqlite3
```

The database contains bounded report evidence and should be treated as sensitive local data. It
does not store raw source documents or plaintext credentials. Database files use `0600`; a parent
directory created by RAGScanner uses `0700`.

## Inspect history

```bash
ragscanner history list
ragscanner history list --format json --limit 20 --offset 0
ragscanner history show HISTORY_ID --verbose
ragscanner history show HISTORY_ID --format json
```

`history_id` identifies one persisted execution snapshot. The report's Core `scan.id` may repeat
for equivalent scan configurations and is displayed separately.

## Compare scans

```bash
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID --format json
```

Comparison uses stable finding fingerprints. It reports new, recurring, severity-changed, and
missing findings. A missing baseline finding is called `resolved` only when assessment coverage and
rule-pack version are compatible. Otherwise it is `not_observed`. Different sources or scan types
refuse finding-lifecycle comparison rather than implying a relationship.

The same list, detail, and comparison use cases are exposed through the read-only localhost API:

```bash
ragscanner serve
```

See the [local API reference](api.md). The API does not create or delete scans in this slice.

## Retention and migrations

No automatic retention cleanup runs. Delete a record explicitly:

```bash
ragscanner history delete HISTORY_ID
ragscanner history delete HISTORY_ID --yes
```

Packaged Alembic migrations run when the database is opened. Before an existing older or unversioned
database is upgraded, a timestamped `*.backup-*` SQLite copy is created beside it. Backups are not
removed automatically. Corrupt databases fail closed with a bounded error.

The API, dashboard, job worker, configurable retention, artifact directory, and administrative
recovery commands are not implemented yet.
