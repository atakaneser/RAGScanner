# Yerel geliştirme

## Gereksinimler

- Python 3.12+
- uv

## Kurulum ve kontroller

```bash
uv sync
uv run ragscanner --version
uv run ragscanner doctor
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

`doctor` ağ bağlantısı kurmaz ve credential gerektirmez. `.env.example` yalnız inert yerel ayarlar içerir.

API, dashboard, worker, connector, parser, scanner ve Docker çalıştırma komutları henüz yoktur. Bunlar uygulandıklarında ve CI tarafından doğrulandıklarında belgelenecektir.

