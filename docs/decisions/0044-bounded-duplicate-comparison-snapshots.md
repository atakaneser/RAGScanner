# ADR-0044: Bounded duplicate comparison snapshots

**Status:** Accepted

## Context

A duplicate finding previously retained only one canonical excerpt and opaque related item IDs.
Readers could not see what was compared, where the other occurrences were found, or why an exact
or lexical-near match was reported. Short classification labels and headings could also create
disproportionate findings and reduce the efficiency score.

## Decision

- Report schema 1.5 stores a bounded, redacted excerpt and source provenance for every retained
  duplicate-group member.
- The canonical member is a stable reporting reference only. It is not a keep, delete, newest, or
  authoritative decision.
- Dashboard, standalone HTML, Excel, and PDF present duplicate members together, with match type,
  similarity, source, page, line range, and estimated redundant tokens.
- Lexical-near groups retain a bounded set of common token shingles as explanatory phrases.
- Duplicate chunk analysis ignores chunks below both materiality gates: at least 48 characters and
  at least six tokens. Complete-document duplicate analysis is unchanged.
- Historical report snapshots remain readable. When member details are absent, the UI requests a
  rerun instead of pretending that a one-sided excerpt is sufficient.

## Consequences

Duplicate findings become auditable without exposing complete documents or enabling automatic
deletion. Short template fragments no longer affect findings or efficiency scores. Reports are
slightly larger, but member count, evidence length, metadata, HTML, JSON, cell, and PDF occurrence
limits remain enforced at the report boundary.
