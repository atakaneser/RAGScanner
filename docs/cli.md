# CLI

## Guided use

After the one-time installation, normal users can start with:

```bash
ragscanner
```

The flow only lists immediate folders whose names indicate a likely RAG source, and labels them as
name-based candidates rather than verified RAG data. It never treats generic folders such as
Documents or the current working directory as an automatic RAG candidate. When OpenWebUI is selected,
available Docker, Podman, nerdctl, and Finch CLIs are inspected only after consent. Only bounded
running-container names, images, and published-port metadata are read without a shell, and only
OpenWebUI candidates are presented. Candidate loopback health endpoints are then checked without
redirects. A separate consent step and an API
key held only in memory can inventory accessible knowledge bases plus linked and standalone/chat
file metadata. Discovery itself does not retrieve document content or prove version compatibility.
Knowledge-base results remain visible even if a later file-inventory endpoint is unavailable. The
inventory uses the selected knowledge bases' supported file endpoints and does not request file
content. In option 2, the flow offers a numbered knowledge-base selection and a separate
content-consent prompt before it starts one immediate local scan. The API key remains only in the
CLI process memory; durable `jobs enqueue-openwebui` remains available for automation.

The bare-command menu contains only two scan routes: a local file or folder, and an OpenWebUI API
knowledge base. Detection-only platform inventory is not presented as a scan route.

The dashboard at `http://localhost:8765` offers bounded discovery only for responsive local
OpenWebUI services, can transfer a discovered URL into its source form, and can list knowledge bases
using an `env:` credential reference. The key is resolved only in the local dashboard/worker process
and is never sent to the browser, report, SQLite database, or job payload. The dashboard can process
one already-consented queued job immediately. Normal installation uses the machine-wide Host Service;
it remains available and processes queued work without an interactive user session.

Neither dashboard nor terminal setup presents detected vector databases as sources. Scanning one
would require a platform-specific connector that can enumerate authorized collections and retrieve
bounded payload text plus stable document/chunk provenance; those connectors are not implemented.

Guided HTML reports are written to the platform-native RAGScanner data directory, never the shell's
current directory. Run `ragscanner paths` to see the exact data, report, and history locations.

## Explicit commands

Use explicit commands for automation and advanced operation:

```bash
ragscanner --version
ragscanner doctor
ragscanner paths
ragscanner install
ragscanner install --mode terminal
ragscanner open
ragscanner status
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/one-large.pdf
ragscanner scan ./knowledge-base --format html --output report.html
ragscanner scan ./knowledge-base --save-history
ragscanner scan ./knowledge-base --rag-profile policy_procedure --retrieval-top-k 6
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
ragscanner quality calibrate ./calibration/manifest.json --minimum-precision 0.95 --minimum-recall 0.90
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

`ragscanner install` is the single elevated installation entry point. It creates the isolated
machine runtime, starts the always-on Host Service on the fixed `http://localhost:8765` address,
and opens the first-run local-administrator dashboard. The server binds only to `127.0.0.1`; it does
not register a custom hostname or expose the dashboard on the network. Use `--mode terminal` to complete initial
source setup in the CLI or `--no-open-dashboard` for a headless installation. Running bare
`ragscanner` or `ragscanner open` opens the dashboard; `ragscanner status` reports installation
locations. `update`, `repair`, and `uninstall` manage the same installation.

On Windows, the Host process is a boot-triggered Task Scheduler task running under `SYSTEM`; it does
not depend on an interactive sign-in and is configured to restart after failure. Linux uses a system
`systemd` unit and macOS uses a system `LaunchDaemon`.

Legacy `agent`, `host`, and `setup` command groups remain hidden only for alpha compatibility
and internal service-manager execution. They are not separate installation choices.

`ragscanner serve` starts the dashboard and versioned API at the same fixed
`http://localhost:8765` address without a worker. `--history-db` selects another database; the port
cannot be changed. History reads are local; API scan/job
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

The persistent data root is `%ProgramData%\RAGScanner` on Windows,
`/Library/Application Support/RAGScanner` on macOS, and `/var/lib/ragscanner` on Linux. Disposable
interactive cache data uses the signed-in user's platform cache directory. `RAGSCANNER_DATA_DIR`
remains an explicit development/automation override. Explicit `--output`, `--database`, and
`--history-db` paths remain under user control.

## Installation maintenance

- `ragscanner update` replaces the isolated machine runtime and restarts the Host Service while
  preserving machine reports, history, and settings.
- `ragscanner repair` fully reinstalls the machine runtime and re-registers/starts the Host
  supervisor, so it also repairs a missing Windows task, systemd unit, or LaunchDaemon.
- `ragscanner uninstall` requires administrator permission and removes the Host Service, machine
  runtime, hostname mapping, and bootstrap tool while preserving reports/history by default. Add
  `--purge-data` to permanently delete the machine-owned data directory. On Windows it
  schedules the removal after the CLI launcher exits, avoiding locked-file access-denied failures.
- `ragscanner uninstall --yes` is the non-interactive form.

Machine installation uses an isolated `uv` tool directory outside user profiles. Windows uninstall
uses short-lived cleanup command files only to defer locked executable removal until the launcher
has exited.

Add optional advisory analysis to a direct scan:

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
ragscanner scan ./knowledge-base --ai-provider openrouter \
  --ai-model openai/gpt-4.1-mini --ai-credential-ref env:OPENROUTER_API_KEY \
  --consent-remote-ai --save-history
```

AI is off unless `--ai-provider` is supplied. Remote analysis requires HTTPS, an external credential
reference, and `--consent-remote-ai`. Only a bounded redacted finding summary is transmitted.
