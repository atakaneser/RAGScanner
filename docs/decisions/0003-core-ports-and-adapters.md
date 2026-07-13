# ADR-0003: Hexagonal scanner core

- Status: Proposed
- Date: 2026-07-12

## Context

The scanner must support CLI, API, workers, multiple sources/vector systems, providers, persistence options, and future MCP without coupling core rules to any one of them.

## Decision

Organize the core as domain values and application services around explicit ports. External parsers, sources/connectors, stores, embedding/chat providers, clocks, IDs, queues, notifications, and delivery mechanisms are adapters wired only at composition roots. Domain modules cannot import adapter SDKs. Use typed versioned inputs/outputs and contract tests for each adapter.

## Consequences

Rules remain reusable and deterministic tests are easy. Interfaces add design work and should not become one-method abstractions without a real boundary. Import/layer checks must enforce the dependency direction.

