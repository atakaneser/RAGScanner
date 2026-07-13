# CLI

## Guided use

After the one-time installation, normal users can start with:

```bash
ragscanner
```

The English onboarding flow can start a local file or folder scan. When OpenWebUI is selected,
available Docker, Podman, nerdctl, and Finch CLIs are inspected only after consent. Only bounded
running-container names, images, and published-port metadata are read without a shell. Candidate
loopback health endpoints are then checked without redirects. A separate consent step and an API
key held only in memory can inventory accessible knowledge bases plus linked and standalone/chat
file metadata. Discovery itself does not retrieve document content or prove version compatibility.
The flow then points to the separate consent-gated `jobs enqueue-openwebui` content workflow.

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
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history show HISTORY_ID --verbose
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner history delete HISTORY_ID
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs enqueue-openwebui --help
ragscanner jobs list
ragscanner jobs show JOB_ID
ragscanner jobs cancel JOB_ID
ragscanner jobs retry JOB_ID
ragscanner worker
ragscanner serve
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
`--max-findings`, `--config`, `--security-only`, `--quality-only`, `--quiet`, `--verbose`,
`--no-color`, `--save-history`, and `--history-db`. Existing output files are not overwritten.
History is never persisted unless `--save-history` or `--history-db` is supplied. See the
[scan pipeline](scan-pipeline.md) for exit codes and [local history](persistence.md) for storage,
migration, retention, and comparison semantics.

`history list` supports bounded `--limit`/`--offset` pagination and terminal or JSON output.
`history show` renders a persisted snapshot, `history compare` performs coverage-aware comparison,
and `history delete` requires confirmation unless `--yes` is supplied. History commands default to
`.ragscanner/history.sqlite3`; `--database` selects another file.

`jobs enqueue-scan` and `jobs enqueue-openwebui` add durable work; `list`, `show`, `cancel`, and
`retry` manage it. `ragscanner worker` executes queued scans, while `--once` processes at most one
job. All default to `.ragscanner/history.sqlite3`; `--database` selects another file.

`ragscanner serve` starts the dashboard and versioned API on `127.0.0.1:8000`. `--port` changes the
loopback port and `--history-db` selects another database. History reads are local; API scan/job
mutation requires `RAGSCANNER_API_KEY`. See the [local API](api.md) and [durable jobs](jobs.md).

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
