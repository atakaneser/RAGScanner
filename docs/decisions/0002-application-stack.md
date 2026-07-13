# ADR-0002: Python modular monolith and server-rendered dashboard

- Status: Accepted
- Date: 2026-07-12

## Decision

Use a Python scanner core, Typer CLI, FastAPI API, and Jinja2/HTMX dashboard. Next.js is not part of
the first release. API and worker may run as separate processes from the same distribution; this is
not a microservice split.

## Rationale

One language/toolchain, direct Pydantic view models, low Docker/RAM cost, and sufficient interaction
for scan/finding workflows reduce initial complexity. Reconsider a separate frontend only if
measured UI needs exceed the server-rendered approach.

## Consequences

The frontend ecosystem is narrower, but maintenance and deployment cost remain low. Raw HTML or
model evidence may never be passed to templates as trusted markup.
