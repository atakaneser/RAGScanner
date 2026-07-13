# ADR-0014: Generic TargetAdapter contract

- Status: Accepted
- Date: 2026-07-12

## Context

Platforms differ in authentication, payload, streaming, and response schemas; Core must not contain
vendor conditions.

## Decision

The target contract includes capability discovery, health checks, authorized invocation,
cancellation, timeout, rate limits, budgets, sessions/correlation, bounded responses, and structured
tool/citation observations. Credentials are opaque secret references.

Evaluation results are `confirmed`, `probable`, `ambiguous`, or `not_detected`. Transport errors,
timeouts, and malformed responses are failed/skipped tests, not vulnerabilities. The first concrete
adapter is Generic REST with declarative mapping and no custom-code execution.

## Consequences

Every platform adapter uses the same fake/contract suite. Generic flexibility requires strict
allowed-host policy and bounded parsing.
