# Contributing

RAGScanner is currently a technical alpha with a working local static scan pipeline. Start from a
scoped issue in `docs/issues/` and do not implement a later milestone without an accepted
boundary/ADR.

## Workflow

1. Create a feature branch from protected `main` (for example `feat/rs-003-python-scaffold`).
2. Keep changes focused and add/update tests and documentation.
3. Use conventional commits such as `feat(core): ...`, `fix(parser): ...`, `docs(adr): ...`.
4. Run the issue’s checks locally, summarize risks and compatibility impact, and open a pull request.
5. Require review/CI before merge; do not force-push `main`.

## Quality gates

Run the current Python gates before opening a pull request:

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

CI repeats lint, formatting, type checking, tests, package/report smoke tests, local Markdown link
checks and secret scanning on Python 3.12 and 3.13. Dependency review runs on pull requests. Web and
container gates will be added with those components; they are not current requirements.

Use deterministic fake providers in CI. Tests must not require real cloud credentials or network access. Synthetic fixtures must not resemble real credentials or personal data.

## Pull requests

State the objective, linked issue, approach, tests, security/privacy impact, docs changes, migrations/compatibility, screenshots only where useful, and rollback plan. CODEOWNERS enforcement and exact approval counts are open decisions before implementation.
