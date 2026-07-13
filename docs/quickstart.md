# Quickstart

```bash
uv sync
uv run ragscanner scan ./examples/sample-kb
```

Standalone HTML raporu:

```bash
uv run ragscanner scan ./examples/sample-kb \
  --format html \
  --output ragscanner-report.html
```

Komut TXT, Markdown, PDF ve DOCX'i bounded olarak işler; static security, exact/near duplicate ve
chunk-quality analizlerini tamamen offline çalıştırır. URL fetch, telemetry veya external AI yoktur.
Örnek bilgi tabanı tamamen sentetiktir.
