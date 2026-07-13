# Alpha release checklist

Target package version: `0.1.0a1` (release title: `v0.1.0-alpha.1`).

## Blocking approvals

- [x] Repository owner approved Apache-2.0 and matching `LICENSE`/package metadata.
- [x] Canonical repository is `https://github.com/atakaneser/RAGScanner`; private reports use
      GitHub Security Advisories.
- [ ] Intended files are reviewed and committed from a clean checkout.

Do not tag, publish, or create a GitHub release while any blocker remains.

## Verification

```bash
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
```

Install the wheel into a fresh environment, run `ragscanner --version`, then create terminal, JSON
and HTML reports from synthetic data. Validate JSON schema and inspect HTML for escaping, CSP,
external assets, absolute paths and secrets.

## Scope

First alpha provides local TXT/Markdown/PDF/DOCX scanning, normalization, chunking, static security,
exact/lexical near duplicates, chunk-quality heuristics, partial product-defined scores and three
report formats. Single-file and multi-file knowledge bases are supported. No database, OpenWebUI,
dashboard, scheduler, OCR, embeddings, remote model or retrieval/answer/freshness assessment exists.
