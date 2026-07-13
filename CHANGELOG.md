# Changelog

## Unreleased

- Added report schema 1.1 ingestion issues, a concise terminal summary, and an HTML executive
  summary with partial-coverage and per-file remediation guidance.
- Established English as the canonical project and runtime language while retaining localized
  README entry points and multilingual scanner inputs; migrated canonical documentation and added a
  regression audit.
- Added CLI and filesystem tests for spaces, parentheses, Turkish, German, Arabic, Cyrillic, Chinese,
  emoji, and decomposed-Unicode filenames.
- Added shell-free `ragscanner update`, `ragscanner repair`, and confirmed `ragscanner uninstall`
  commands for uv-managed installations.
- Added English guided local scanning and consent-based OpenWebUI service-candidate discovery to the
  bare `ragscanner` command.
- PDF signature, zero-page, and PyMuPDF page-count failures now produce typed categories and
  remediation; one malformed file does not stop a collection scan.
- Documented a one-time `uv tool install` flow that does not require cloning the repository.
- Made the root README canonical English documentation and added Turkish, German, French,
  Simplified Chinese, and Italian localized README pages.

All notable project changes will be documented here. The project intends to follow Semantic Versioning once releasable artifacts exist and Keep a Changelog structure.

## [0.1.0-alpha.1] - Unreleased

### Added

- Milestone 0 product-foundation documentation, architecture decisions, roadmap, and implementation issue drafts.
- uv/Python src-layout scaffold, Typer CLI, Pydantic configuration/diagnostics, structured logging and CI.
- Framework-independent static/active/shared domain models with authorization, safety, fingerprinting, redaction and validation contracts.
- Deterministic offline terminal, versioned JSON and standalone HTML reporting with boundary redaction, filters and limits.
- Unified local static scan pipeline and `ragscanner scan` CLI with isolated file stages, assessed-only scoring, progress events, TOML configuration and atomic reports.
- Single-source and small multi-source knowledge bases with explicit assessment coverage.
- Alpha package metadata, bundled rules/schema, build verification and synthetic release assets.

No product version has been released.
