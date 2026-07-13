# ADR-0020: Packaged localhost read-only API composition

- Status: Superseded by ADR-0022
- Date: 2026-07-14

## Decision

Place the initial application services in `ragscanner.application` and the FastAPI delivery adapter
in `ragscanner.api` within the existing Python distribution. The CLI and API compose the same
database-independent history service. A separate deployable `apps/api` package is deferred until a
distinct deployment boundary provides measured value.

The first API slice is read-only and exposes versioned health, history list, report detail, and
comparison endpoints. `ragscanner serve` binds Uvicorn to `127.0.0.1` with no configurable external
host. Requests require an allowed loopback/test Host header, have a bounded declared body size, and
receive stable generic error envelopes and defensive response headers.

This initial slice deliberately had no browser accounts or API keys because it cannot be bound to an
external interface. Authenticated external access, asynchronous scan creation, idempotency keys,
rate limiting, tenant scope, and connector control remain blocked on the API-auth contract and a
production scan handler. The durable job contract now exists internally but is not exposed here.
Write capabilities were later added under the scoped local authentication boundary in ADR-0022.

## Rationale

A thin delivery adapter validates the application-service boundary and unblocks the future
dashboard without prematurely introducing a deployment split or unauthenticated remote control
surface. Read-only localhost access is useful for local automation while keeping the alpha threat
surface bounded.

## Consequences

- CLI and HTTP delivery reuse history behavior without importing FastAPI into Core.
- OpenAPI describes the available read contract but is not yet the complete RS-029 contract.
- External reverse-proxy deployment is unsupported until authentication and trusted-proxy behavior
  are designed and tested.
- The future worker and scan-create endpoint must call application services rather than CLI
  functions or database adapters directly.
