# ADR-0029: Machine-local Host Service and dashboard hostname

## Status

Accepted

## Context

The per-user desktop Agent cannot process RAG scans when the user is signed out. This is unsuitable
for an always-on OpenWebUI Docker host. The dashboard must remain local and must not require public
DNS or an internet account.

## Decision

RAGScanner provides a separate elevated **Host Service**. It runs the localhost dashboard/API and
one durable worker independently of interactive user sessions. The installer can add exactly one
marked hosts-file entry mapping `local.ragscanner.com` to `127.0.0.1`; it never modifies public DNS
or makes the dashboard reachable from another machine.

The Host Service has a first-run dashboard bootstrap screen. It creates one local administrator with
an scrypt password hash and an HttpOnly, SameSite=Strict, time-limited local session. No password is
stored in reports, SQLite history, job payloads, logs, or source control.

## Consequences

Host installation requires administrator permission because it changes a machine-wide service and
the hosts file. The dashboard may guide the user, but it cannot silently elevate browser privileges.
Platform service accounts and filesystem access restrictions remain part of deployment hardening;
OpenWebUI access should use a separate non-admin service account and external secret reference.
