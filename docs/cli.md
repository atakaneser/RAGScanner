# CLI

## Guided use

After the one-time installation, normal users can start with:

```bash
ragscanner
```

The default English onboarding choice automatically discovers local RAG environment candidates after
consent. It reads bounded Docker, Podman, nerdctl, and Finch running-container metadata and probes
only approved OpenWebUI loopback health endpoints. It identifies OpenWebUI, Qdrant, Chroma,
Weaviate, Milvus, and pgvector-related containers from their names/images and published loopback
ports. Detection of a non-OpenWebUI platform is an inventory hint only: no connector, collection,
or document access is claimed until that platform has a supported connector.

The flow only lists immediate folders whose names indicate a likely RAG source, and labels them as
name-based candidates rather than verified RAG data. It never treats generic folders such as
Documents or the current working directory as an automatic RAG candidate. When OpenWebUI is selected,
available Docker, Podman, nerdctl, and Finch CLIs are inspected only after consent. Only bounded
running-container names, images, and published-port metadata are read without a shell. Candidate
loopback health endpoints are then checked without redirects. A separate consent step and an API
key held only in memory can inventory accessible knowledge bases plus linked and standalone/chat
file metadata. Discovery itself does not retrieve document content or prove version compatibility.
Knowledge-base results remain visible even if a later file-inventory endpoint is unavailable. The
inventory uses the selected knowledge bases' supported file endpoints and does not request file
content. The flow then points to the separate consent-gated `jobs enqueue-openwebui` content
workflow.

The dashboard at `http://127.0.0.1:8000` offers the same consented local environment discovery,
can transfer a discovered reachable OpenWebUI URL into its scan form, and can list knowledge bases
using an `env:` credential reference. The key is resolved only in the local dashboard/worker process
and is never sent to the browser, report, SQLite database, or job payload. The dashboard can process
one already-consented queued job with **Run next queued job**; `ragscanner worker` remains the
appropriate long-running option.

Guided HTML reports are written to the platform-native RAGScanner data directory, never the shell's
current directory. Run `ragscanner paths` to see the exact data, report, and history locations.

## Explicit commands

Use explicit commands for automation and advanced operation:

```bash
ragscanner --version
ragscanner doctor
ragscanner paths
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
the `history.sqlite3` file shown by `ragscanner paths`; `--database` selects another file.

`jobs enqueue-scan` and `jobs enqueue-openwebui` add durable work; `list`, `show`, `cancel`, and
`retry` manage it. `ragscanner worker` executes queued scans, while `--once` processes at most one
job. All default to the central `history.sqlite3` file shown by `ragscanner paths`; `--database`
selects another file.

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

The default data root is `%LOCALAPPDATA%\RAGScanner` on Windows,
`~/Library/Application Support/RAGScanner` on macOS, and `$XDG_DATA_HOME/RAGScanner` (or
`~/.local/share/RAGScanner`) on Linux. `RAGSCANNER_DATA_DIR` overrides this root. Explicit
`--output`, `--database`, and `--history-db` paths remain under user control.

## Installation maintenance

- `ragscanner update` upgrades the installed uv tool environment.
- `ragscanner repair` fully reinstalls that environment while retaining its source/settings.
- `ragscanner uninstall` asks for confirmation and removes the uv tool environment. On Windows it
  schedules the removal after the CLI launcher exits, avoiding locked-file access-denied failures.
- `ragscanner uninstall --yes` is the non-interactive form.

Maintenance commands invoke the resolved `uv` executable directly without a shell and preserve its
exit status. Windows uninstall uses a short-lived generated command file solely to defer the same
direct `uv tool uninstall ragscanner` invocation until the launcher has exited. They require an
installation managed by `uv tool`.
