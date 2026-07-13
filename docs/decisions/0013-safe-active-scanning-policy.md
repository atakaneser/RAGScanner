# ADR-0013: Safe active-scanning policy

- Status: Accepted
- Date: 2026-07-12

## Context

Active tests may create tool, email, shell, file, or database side effects. Unauthorized use also
creates legal and operational risk.

## Decision

Active Scan requires explicit target-owner authorization and defaults to the `safe` profile.
Destructive or side-effect-capable payloads are never default and cannot enter that profile.
Tool-use tests use canary, dry-run, or no-op actions.

TargetAdapter must support allowed-host/SSRF policy, TLS, timeout, rate limits, request/token budgets,
cancellation, response-size limits, and credential references. Secret values never enter logs,
reports, or artifacts.

## Consequences

Some real tool-abuse vulnerabilities may remain probable or ambiguous under safe testing. Safety and
authorization take priority over coverage.
