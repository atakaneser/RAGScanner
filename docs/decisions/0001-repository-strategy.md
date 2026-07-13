# ADR-0001: Single open-source repository

- Status: Proposed
- Date: 2026-07-12

## Context

All RAGScanner development is free and open source. There is no paid edition, closed module,
entitlement, or artificial feature restriction.

## Decision

Core, CLI, SDK, API, worker, OpenWebUI connector, dashboard, scheduler, security rules, and
documentation are developed modularly in one public repository. Core remains independent of UI,
connectors, model providers, and database adapters.

## Consequences

Contribution, issue tracking, versioning, and security updates remain straightforward. Repository
growth requires path-based CI and clear module ownership. Documentation may be published from the
same repository; a separate deployment project needs a concrete technical reason.
