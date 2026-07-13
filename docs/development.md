# Local development

Requirements: Python 3.12 or 3.13 and `uv`.

```bash
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

`doctor` performs no network request and requires no credential. `.env.example` contains inert local
settings only. API, dashboard, worker, production OpenWebUI connector, and Docker commands will be
documented only after their implementations and CI checks exist.
