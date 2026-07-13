# Quickstart

Installed users:

```bash
ragscanner scan ./examples/sample-kb
ragscanner scan ./examples/sample-kb --format html --output ragscanner-report.html
```

Contributors may use `uv run ragscanner ...` from the repository root. The command processes TXT,
Markdown, PDF, and DOCX under explicit limits, then runs offline static security, exact/near
duplicate, and chunk-quality analysis. It performs no URL fetch, telemetry, or external AI call.
The sample knowledge base is entirely synthetic and intentionally multilingual.
