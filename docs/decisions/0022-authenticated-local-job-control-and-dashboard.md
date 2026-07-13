# ADR-0022: Authenticated local job control and dashboard composition

- **Status:** Accepted
- **Date:** 2026-07-14

## Context

RAGScanner needs asynchronous scan creation and job control without turning the technical-alpha
localhost service into a public, multi-user platform. Browser forms must not receive or persist API
credentials, and Core must remain independent of FastAPI and Jinja.

## Decision

The packaged service remains bound to `127.0.0.1`. History reads remain loopback-local. Scan-create
and job-control API routes require a Bearer key held as a one-way hash in process memory, a named
scope, and an in-memory per-key rate limit. The initial environment composition reads one key from
`RAGSCANNER_API_KEY`; programmatic composition may provide multiple scoped keys.

The Jinja dashboard is a same-origin localhost interface composed directly over application
services. Mutating browser forms use a strict SameSite, HttpOnly double-submit CSRF token. The
dashboard never embeds the API key. It is not a remote-account or multi-user authentication model.

## Consequences

- API automation gets explicit authorization, idempotent enqueue, cancellation, retry, and stable
  error envelopes.
- The browser remains usable without copying a secret into page state.
- Rate-limit and key state reset with the process, which is acceptable for the local alpha.
- External exposure still requires a trusted reverse proxy or private-network control.
- Multi-user sessions, RBAC, durable key management, and public deployment remain unresolved.
