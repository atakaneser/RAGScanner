# ADR-0024: Platform-native application data paths

- **Status:** Accepted
- **Date:** 2026-07-15

## Context

Relative defaults make storage depend on the process launch directory. On Windows, invoking the
guided CLI from `C:\Windows\System32` therefore attempted to place reports there. Relative history
paths could also create `.ragscanner` directories in unrelated working directories.

## Decision

Use the operating system's per-user application data convention as the single default RAGScanner
root. Disable the optional vendor/author level so there is one `RAGScanner` directory. Store guided
HTML reports below its `reports` directory and the default SQLite database as `history.sqlite3` at
the root. `ragscanner paths` reports the resolved locations without creating them.

`RAGSCANNER_DATA_DIR` remains the explicit root override. Explicit CLI output and database paths
remain authoritative. The application creates a directory only when an operation needs to write
there; inspection commands do not create it.

## Consequences

- Launching RAGScanner from System32 or another unrelated directory no longer places default
  reports or hidden data there.
- Windows, macOS, and Linux installations follow their native per-user data conventions.
- Existing relative `.ragscanner` data is not migrated automatically; users can keep using it with
  `RAGSCANNER_DATA_DIR` or move it explicitly.
- Portable installations can select their own root through the environment override.
