# CLI

Normal users can open the English onboarding flow with this command:

```bash
ragscanner
```

The flow can start a local file or folder scan directly. If OpenWebUI is selected, fixed loopback
health endpoints are checked only after consent. This check does not read document content or prove
that a responding service is OpenWebUI. The flow clearly states that the content connector is not
implemented yet.

Explicit commands remain available for automation and advanced use:

```bash
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./knowledge-base
uv run ragscanner scan ./knowledge-base/one-large.pdf
uv run ragscanner scan ./knowledge-base --format html --output report.html
uv run ragscanner security scan ./knowledge --format json
uv run ragscanner quality scan ./knowledge --format terminal
uv run ragscanner report report-input.json --format html --output report.html
```

`report` seçenekleri: `--format`, `--verbose`, `--severity`, `--category`, `--classification`,
`--rule-id`, `--document`, `--target`, `--max-findings`, `--include-info/--exclude-info`,
`--show-absolute-paths` ve `--output`. HTML için output zorunludur; absolute path varsayılan gizlidir.

Unified `scan`; `--include`, `--exclude`, `--recursive/--no-recursive`, `--max-file-size`,
`--max-files`, `--category`, `--exclude-rule`, `--include-pii`, `--min-severity`, `--fail-on`,
`--max-findings`, `--config`, `--security-only`, `--quality-only`, `--quiet`, `--verbose` ve
`--no-color` seçeneklerini destekler. Çıktı overwrite etmez. Exit kodları için
[scan pipeline](scan-pipeline.md) belgesine bakın.
