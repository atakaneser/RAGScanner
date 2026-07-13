# CLI

## Guided use

After the one-time installation, normal users can start with:

```bash
ragscanner
```

The English onboarding flow can start a local file or folder scan. When OpenWebUI is selected,
fixed loopback health endpoints are checked only after consent. The check does not read document
content or prove that a responding service is OpenWebUI. The production OpenWebUI content connector
is not implemented yet, and the CLI states that limitation explicitly.

## Explicit commands

Use explicit commands for automation and advanced operation:

```bash
ragscanner --version
ragscanner doctor
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/one-large.pdf
ragscanner scan ./knowledge-base --format html --output report.html
ragscanner security scan ./knowledge --format json
ragscanner quality scan ./knowledge --format terminal
ragscanner report report-input.json --format html --output report.html
```

Contributors who have not installed the tool globally may prefix commands with `uv run` from the
repository root.

`report` supports `--format`, `--verbose`, `--severity`, `--category`, `--classification`,
`--rule-id`, `--document`, `--target`, `--max-findings`, `--include-info/--exclude-info`,
`--show-absolute-paths`, and `--output`. HTML requires an output path. Absolute source paths are
hidden by default.

Unified `scan` supports `--include`, `--exclude`, `--recursive/--no-recursive`, `--max-file-size`,
`--max-files`, `--category`, `--exclude-rule`, `--include-pii`, `--min-severity`, `--fail-on`,
`--max-findings`, `--config`, `--security-only`, `--quality-only`, `--quiet`, `--verbose`, and
`--no-color`. Existing output files are not overwritten. See the [scan pipeline](scan-pipeline.md)
for exit codes.

## Path rules

Quote paths containing spaces, parentheses, wildcard characters, or other shell-sensitive text.

```powershell
ragscanner scan "C:\Users\Example\Downloads\Knowledge Base (2026)"
ragscanner scan "C:\Users\Example\Downloads\Kılavuz 📘.pdf"
```

```bash
ragscanner scan "/home/example/Knowledge Base (2026)"
ragscanner scan "/app/backend/data/uploads"
```

Windows paths such as `C:\...` must be used in Windows PowerShell. Container paths such as
`/app/...` exist inside the relevant Linux/container filesystem and may not exist on the host.
RAGScanner preserves Unicode filenames and supports multilingual document content.

## Installation maintenance

- `ragscanner update` upgrades the installed uv tool environment.
- `ragscanner repair` fully reinstalls that environment while retaining its source/settings.
- `ragscanner uninstall` asks for confirmation and removes the uv tool environment.
- `ragscanner uninstall --yes` is the non-interactive form.

Maintenance commands invoke the resolved `uv` executable directly without a shell and preserve its
exit status. They require an installation managed by `uv tool`.
