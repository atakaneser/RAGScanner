# RS-062 — Reporting usability and canonical project language

**Milestone:** M1 usability hardening
**Priority:** P0
**Status:** Complete in working tree; awaiting review/commit

## Objective

Make local scan results understandable without exposing raw implementation detail, and establish
English as the canonical project/runtime language while preserving multilingual scan inputs and the
five localized README pages.

## Scope

- Concise default terminal result with verbose technical detail on demand
- HTML executive summary, partial-coverage warning, and per-file ingestion remediation
- Versioned report contract for ingestion issues
- Canonical English project language ADR and migration audit
- Windows, Linux/container, spaces, parentheses, emoji, and Unicode-normalization path coverage
- Installation, update, removal, and troubleshooting guidance for normal users

## Acceptance

- Partial or failed scans cannot be mistaken for complete healthy scans.
- Files that fail ingestion are separated from security/quality findings and include remediation.
- A score is explicitly scoped to assessed checks and does not imply a security guarantee.
- Default terminal output is concise; `--verbose` exposes evidence and technical details.
- Runtime and canonical documentation are English; multilingual input remains covered by tests.
- Ruff, formatting, strict mypy, pytest, build, link checks, and Graphify refresh pass.

## Delivered

- Report schema 1.1 per-file ingestion issues and remediation
- Concise terminal output with verbose technical detail
- HTML executive summary and assessment-coverage warning
- Canonical English documentation migration plus regression audit
- User/contributor installation separation and cross-platform path guidance
- Unicode and shell-sensitive filename coverage through the CLI and filesystem connector
- Shell-free one-command update, repair, and confirmed uninstall through the uv tool environment
