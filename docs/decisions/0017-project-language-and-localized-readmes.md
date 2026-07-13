# ADR-0017: English canonical project language and localized READMEs

**Status:** Accepted
**Date:** 2026-07-13

## Context

RAGScanner accepts multilingual and Unicode knowledge sources, but mixed-language source code,
runtime messages, schemas, and canonical documentation make maintenance and support inconsistent.
Users still benefit from localized entry-point documentation.

## Decision

- English is the canonical language for source code, runtime output, schemas, tests that describe
  product behavior, issue drafts, ADRs, and project documentation.
- `README.md` is canonical English documentation.
- Turkish, German, French, Simplified Chinese, and Italian README pages are maintained as localized
  entry points and link back to the canonical README.
- Multilingual text remains valid in scanner input, synthetic fixtures, Unicode/path tests, and
  explicit localization tests. The scanner must not restrict document language.
- Planned UI localization requires a separate decision and must not change the English default.

## Consequences

Legacy canonical documents must be migrated to English incrementally and may not be treated as
fully migrated until the language audit passes. Localized README drift must be reviewed when the
canonical quickstart or safety behavior changes.
