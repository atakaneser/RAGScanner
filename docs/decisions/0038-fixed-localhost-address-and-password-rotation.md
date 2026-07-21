# ADR-0038: Fixed localhost address and password rotation

## Status

Accepted

## Context

The product-owned `local.ragscanner.com` hosts-file entry added installation complexity and made the
actual loopback boundary less obvious. Configurable dashboard ports also made shortcuts, readiness
checks, documentation, and service diagnostics disagree. The first-run administrator password could
not be changed without recreating machine data.

## Decision

The dashboard has one canonical address: `http://localhost:8765`. Uvicorn binds only to
`127.0.0.1:8765`; user-facing and hidden service commands do not accept a port override. Install,
update, repair, and uninstall remove the exact legacy RAGScanner hosts-file line when present, and
no command creates a replacement hostname entry. The HTTP Host boundary accepts standard loopback
names only and rejects the retired custom hostname.

An authenticated, CSRF-protected Settings form changes the local administrator password only after
the current password is verified. New passwords require at least 14 characters and are written
atomically as an scrypt hash with a fresh salt. The session signing secret is rotated in the same
replacement, invalidating every existing session; the successful requesting session receives a new
cookie.

## Consequences

All installation modes, documentation, readiness checks, and browser opening use the same memorable
port. A process already using port 8765 must be stopped before RAGScanner can start. Existing
installations drop the retired hosts-file line on the next elevated lifecycle command. Password
changes intentionally sign other browsers out and never place a plaintext password in SQLite,
reports, jobs, logs, or source control.
