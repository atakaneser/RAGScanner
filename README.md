# RAGScanner

> Scan your RAG before your users do.

**English** · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner is a free, open-source, local-first tool for inspecting security and content-quality
risks in RAG knowledge sources. The current technical alpha scans TXT, Markdown, text-based PDF,
and DOCX files, then produces terminal, JSON, or standalone HTML reports.

The current static pipeline does not transmit documents to remote services, does not require an
LLM, does not run telemetry, does not follow links, and never executes detected commands.

> [!WARNING]
> This is a technical alpha. A static scan does not prove that a running RAG application is secure
> and does not provide complete prompt-injection protection. Findings are review inputs, not a
> security guarantee.

## What works today

| Capability | Alpha status |
|---|---|
| Single local file and folder scans | Available |
| TXT, Markdown, text-based PDF, and DOCX | Available |
| Deterministic normalization and source mapping | Available |
| Structure, paragraph, and token-window chunking | Available |
| Versioned static RAG security rules | Available |
| Exact and lexical near-duplicate analysis | Available |
| Chunk-quality checks | Available |
| Terminal, JSON, and standalone HTML reports | Available |
| Offline static scanning | Default behavior |
| Unified machine installation and dashboard launch | `ragscanner install`; bare `ragscanner` opens dashboard |
| Consent-based container OpenWebUI discovery and KB/file metadata inventory | Available |
| OCR and semantic duplicate analysis | Not available yet |
| Opt-in SQLite history and coverage-aware comparison | Available from the CLI |
| Localhost history API | Available with `ragscanner serve` |
| Durable SQLite static-scan jobs and worker | Available |
| Scoped authenticated asynchronous scan/job API | Available on loopback |
| Local overview and queue dashboard | Available with `ragscanner serve` |
| Dashboard report archive, date/source filters, detail, and comparison | Available |
| Remembered non-secret source profiles and Settings/Sources management | Available |
| Per-user Local Agent | Retired; machine service replaces it |
| Machine-local Host Service, runtime, SQLite, and administrator bootstrap | Available |
| Docker, Podman, nerdctl, Finch, Kubernetes, and localhost metadata discovery | Available |
| Consent-gated OpenWebUI knowledge content connector | Available |
| Scheduler and vector-store content connectors | Not available yet |
| Per-scan local/remote AI-assisted report analysis | Available and off by default |
| Active endpoint scan CLI | Not available; core contracts only |

`ragscanner scan` runs the local discovery → parsing → normalization → chunking → static security
→ duplicate analysis → chunk quality → scoring → reporting pipeline.

## Quick start for users

Requirements: Python 3.12 or 3.13 and [`uv`](https://docs.astral.sh/uv/).

Install the alpha directly from GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
# On Windows use an administrator terminal. On macOS/Linux prefix the resolved command with sudo.
ragscanner install
```

`install` creates an isolated machine runtime, starts the service at boot, stores persistent
SQLite state in the operating system's machine data directory, and opens the local dashboard at
`http://local.ragscanner.com:8000`. The bootstrap `uv tool` installation may then be removed; the
service does not depend on a signed-in user's profile.

The bare `ragscanner` command opens the local dashboard. `ragscanner install` uses the dashboard by
default; `ragscanner install --mode terminal` completes initial source setup in the CLI instead.
The web setup creates the machine-local administrator and can remember
the first non-secret source profile. Additional environments can be connected later from Sources.
Automatic filesystem discovery only suggests immediate folders with RAG-oriented names; it does not
treat general folders such as Documents as RAG sources. After explicit consent, OpenWebUI discovery inspects
bounded metadata from available Docker, Podman, nerdctl, Finch, or the active Kubernetes context,
plus common loopback
addresses. A separately supplied in-memory API key can inventory accessible knowledge bases plus
knowledge-linked and standalone/chat files. Option 2 then lets the user select one listed OpenWebUI
knowledge base and, after separate explicit content consent, run the static pipeline in the same
local process.

Maintain or remove the installation with one RAGScanner command:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner status
ragscanner open
```

These commands require administrator permission. `update` and `repair` replace the isolated machine
runtime and restart the Host Service. `uninstall` removes the service, runtime, and hostname mapping
while preserving reports/history unless `--purge-data` is explicitly provided. Automation may use
`ragscanner uninstall --yes`. On Windows, locked runtime removal is deferred until the launcher exits.

After a PyPI release, installation will use `uv tool install ragscanner`. No PyPI package or release
tag has been published yet.

## Direct scans

AI-assisted analysis can be chosen per direct scan or dashboard job. Local providers include Ollama,
LM Studio, LocalAI, and vLLM. Remote choices include OpenRouter, OpenAI, NVIDIA NIM, Anthropic,
Google Gemini, Groq, Mistral AI, Together AI, and custom OpenAI-compatible endpoints.

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
ragscanner scan ./knowledge-base --ai-provider openrouter \
  --ai-model openai/gpt-4.1-mini --ai-credential-ref env:OPENROUTER_API_KEY \
  --consent-remote-ai --save-history
```

AI is off by default. Remote choices require explicit consent for that scan. Only bounded, redacted
scores, coverage, and finding summaries are sent; raw documents and finding evidence are excluded.
If a provider fails, the deterministic report remains complete and authoritative.

Use quotes around paths containing spaces, parentheses, or other shell-sensitive characters.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Create explicit export files for automation or compatibility:

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Save and compare local scan history only when requested:

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

Guided CLI scans and dashboard jobs save a versioned report snapshot to local history and do not
create standalone HTML files. Open Reports in the dashboard to filter by date/source, inspect a
report, or compare two executions. Direct `--format json` and `--format html` exports remain
available when a caller explicitly requests an output file.

Queue durable scans and run the worker:

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

For a consented OpenWebUI scan, keep the credential outside SQLite:

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` opens the local dashboard. Set `RAGSCANNER_API_KEY` to enable scoped Bearer-
authenticated scan creation and job control through the API. The server binds only to `127.0.0.1`.

RAGScanner does not overwrite an existing output file by default.

## Complete CLI command reference

Run `ragscanner COMMAND --help` for the installed version's authoritative syntax. The commands below
are the complete public interface; internal compatibility commands are intentionally hidden.

### Invocation and diagnostics

| Command | Detailed use |
| --- | --- |
| `ragscanner` | Opens the dashboard when RAGScanner is installed; otherwise prints the installation command. |
| `ragscanner --version` | Prints the installed CLI version. |
| `ragscanner --help` / `ragscanner COMMAND --help` | Shows global help or command-specific options without changing machine state. |
| `ragscanner --install-completion` / `--show-completion` | Installs shell completion or prints the completion script supported by Typer. |
| `ragscanner doctor` | Runs offline installation, path, configuration, parser, and runtime diagnostics. |
| `ragscanner paths` | Prints the machine configuration, data, report, temporary, and legacy path locations for the current OS. |

### Machine installation and lifecycle

| Command | Detailed use |
| --- | --- |
| `ragscanner install` | Installs the isolated machine runtime and system service, configures `local.ragscanner.com`, initializes machine data, and opens the dashboard. Requests administrator elevation when required. |
| `ragscanner install --yes` | Accepts routine installation prompts for unattended provisioning; OS elevation may still be required. |
| `ragscanner install --mode terminal` | Completes installation through terminal setup instead of the default dashboard setup. Valid modes are `dashboard` and `terminal`. |
| `ragscanner install --no-open-dashboard` | Installs everything without launching a browser after completion. |
| `ragscanner open` | Opens the installed dashboard in the default browser. It does not start a second foreground server. |
| `ragscanner status` | Displays the machine installation, service, dashboard, runtime, and data-path state. |
| `ragscanner update` | Replaces the isolated runtime with the current package version and restarts the machine service; administrator permission is required. |
| `ragscanner repair` | Reconciles missing runtime, service, hostname, directories, and configuration components; administrator permission is required. |
| `ragscanner uninstall` | Removes the service, runtime, and hostname mapping after confirmation while preserving reports and history. |
| `ragscanner uninstall --yes --purge-data` | Performs non-interactive removal and also deletes machine configuration, report history, and managed data. This is destructive. |

### Direct local scans

```text
ragscanner scan PATH [OPTIONS]
```

`PATH` may be a supported file or a directory. Quote paths containing spaces or shell-sensitive
characters. Direct scans run locally and AI enrichment is disabled unless explicitly selected.

| Option | Detailed use |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | Selects terminal output or an explicit JSON/HTML export. File exports require an output path and do not overwrite an existing file. |
| `--include GLOB`, `--exclude GLOB` | Narrows directory discovery with include/exclude glob patterns. These options may be repeated. |
| `--recursive` / `--no-recursive` | Enables or disables descent into subdirectories; recursion is enabled by default. |
| `--max-file-size BYTES`, `--max-files COUNT` | Applies positive safety limits to discovered input size and file count. |
| `--category NAME`, `--exclude-rule ID` | Includes selected rule categories or removes selected rule IDs; repeat the option for multiple values. |
| `--include-pii` / `--no-include-pii` | Enables or disables PII-oriented rules in the effective scan policy. |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | Filters displayed findings, selects the severity that produces a nonzero exit, and bounds report volume. |
| `--config FILE` | Loads scan policy from an explicit configuration file instead of only defaults and machine configuration. |
| `--security-only`, `--quality-only` | Runs only the security family or only the quality family. Do not combine the two switches. |
| `--quiet`, `--verbose`, `--no-color` | Controls terminal detail and ANSI color without changing scan results. |
| `--save-history`, `--history-db FILE` | Persists a versioned report snapshot and optionally selects a non-default SQLite history database. |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | Enables optional report enrichment with the selected provider/model and an optional compatible endpoint. |
| `--ai-credential-ref REF`, `--consent-remote-ai` | Resolves a credential externally, such as `env:OPENROUTER_API_KEY`, and records required consent for a remote provider. |

### AI report enrichment

| Command or option | Detailed use |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | Enriches an existing supported report file and writes a new report; both model and output are required. |
| `--provider NAME` | Selects the analysis provider; it defaults to `ollama`. Supported configured choices include local and remote OpenAI-compatible providers. |
| `--base-url URL`, `--credential-ref REF` | Overrides the provider endpoint and resolves its secret outside report/history content. |
| `--consent-remote` | Explicitly permits bounded, redacted report-summary transmission to a remote analysis provider. Raw documents and evidence are excluded. |

### Durable jobs and worker

| Command | Detailed use |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | Queues a durable local file/folder scan. Accepts `--database`, `--config`, `--idempotency-key`, `--max-attempts`, and the direct-scan AI options. |
| `ragscanner jobs enqueue-openwebui` | Queues an OpenWebUI knowledge scan. Requires `--base-url`, `--knowledge-id`, `--credential-ref`, and `--consent-content`; also accepts database, idempotency, retry, and AI options. |
| `ragscanner jobs list` | Lists queued and completed jobs with `--database`, `--limit` (1–200), `--offset`, and `--format`. |
| `ragscanner jobs show JOB_ID` | Shows one job, its attempts, timestamps, result reference, and error state; `--database` selects storage. |
| `ragscanner jobs cancel JOB_ID` | Cancels a job that has not reached a terminal state; `--database` selects storage. |
| `ragscanner jobs retry JOB_ID` | Creates another runnable attempt for an eligible failed/cancelled job; `--database` selects storage. |
| `ragscanner worker` | Continuously leases and executes durable jobs from the machine job database. |
| `ragscanner worker --once` | Processes available work once and exits, which is useful for tests and scheduled invocations. |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | Worker controls for storage, polling (0.1–60), leases (5–3600), and stable worker identity. |

### Stored report history

| Command | Detailed use |
| --- | --- |
| `ragscanner history list` | Lists stored scans. Accepts `--database`, `--limit` (1–200), `--offset`, and `--format`. |
| `ragscanner history show SCAN_ID` | Renders one stored report with `--database`, `--format`, and optional `--verbose` evidence detail. |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | Compares two stored executions and reports new, resolved, and unchanged findings; accepts `--database` and `--format`. |
| `ragscanner history delete SCAN_ID` | Deletes one stored report after confirmation. Use `--yes` only for deliberate automation; `--database` selects storage. |

### Rendering and foreground service

| Command | Detailed use |
| --- | --- |
| `ragscanner report SCAN_RESULT` | Re-renders a scan-result file with `--format`, `--output`, `--verbose`, severity/category/classification/rule/document/target filters, `--max-findings`, `--include-info` or `--exclude-info`, and optional `--show-absolute-paths`. |
| `ragscanner serve` | Runs the dashboard/API in the foreground on loopback for development or diagnostics; normal installed use relies on the machine service. |
| `ragscanner serve --port PORT --history-db FILE` | Selects the loopback port (1–65535) and an alternate report-history database. |

### Specialized scanners

| Command | Detailed use |
| --- | --- |
| `ragscanner security scan PATH` | Runs only security rules. Supports rule/category/severity filters, `--format`, `--fail-on`, `--max-findings`, `--include-pii`, and `--offline` or `--no-offline`; offline is the default. |
| `ragscanner quality scan PATH` | Runs quality checks with independent exact-duplicate, near-duplicate, and chunk-quality switches plus `--similarity-threshold` (0.5–1.0), chunk-token bounds, `--fail-on`, and `--format`. |

### Operational rules

| Rule | Meaning |
| --- | --- |
| Exit status | Invalid input, operational failure, or a finding at/above `--fail-on` produces a nonzero exit suitable for CI. |
| Consent | OpenWebUI document access and remote AI use require their explicit consent switches; metadata-only discovery does not grant content access. |
| Credentials | Store secrets in environment variables or another supported external resolver and pass only a credential reference. |
| Storage | Omitted database/output paths resolve to the OS-specific machine locations displayed by `ragscanner paths`. |
| Services | The installed dashboard/worker is machine-scoped; temporary foreground `serve` and `worker` commands remain available for diagnostics. |
| Output safety | Existing export files are not overwritten, absolute source paths are hidden by default, and report evidence is bounded and escaped. |
| Compatibility | Option names and command output are English; scanned RAG content remains Unicode-native in every supported language. |

## Multilingual input

Product-generated UI labels, status text, error messages, remediation, metadata, and canonical
documentation are English. RAG sources remain Unicode-native and may contain Turkish, German,
French, Chinese, Italian, Arabic, Cyrillic, CJK, emoji, and NFC/NFD filename variants.

Source-derived evidence is preserved in its original language to maintain audit fidelity. The
localized README files are the only intentional non-English project documentation.

## Understanding reports

Reports distinguish:

- scan completion status and partial coverage;
- severity from confidence;
- `confirmed`, `probable`, `ambiguous`, and `not_detected` classifications;
- assessed, partial, failed, and `not_assessed` checks;
- document, page, chunk, and source locations when available;
- scanner, rule-pack, and policy versions.

`not_assessed` does not mean healthy or zero risk. A security score is not a security guarantee.
Static scanning and authorized active endpoint testing are separate modes.

## Privacy and security model

- Static scans are local and make no hidden network calls.
- Document, chunk, and finding-evidence content is not sent to optional AI providers; only a bounded,
  redacted report summary may be sent after explicit per-scan consent.
- URLs may be parsed but are not fetched.
- Suspicious payloads, macros, shell commands, and embedded objects are not executed.
- DOCX external relationships are not followed; PDF attachments are not extracted.
- Evidence is bounded, HTML-escaped, and masked for secret-like patterns.
- Absolute source paths are hidden in reports by default.
- There is no telemetry, billing, subscription, entitlement, or license server.

Remote connectors and optional models remain disabled until explicitly configured and consented
to. OpenWebUI content access requires a selected knowledge base, external credential reference,
and explicit consent; it is one integration, not the product core.

## Installation for contributors

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

Quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

All fixtures must be synthetic. Never add real credentials, customer documents, or personal data.

## Architecture

The core remains independent of UI frameworks, databases, connectors, model vendors, and MCP.
Integration roles are deliberately separate:

- `SourceConnector` reads documents, chunks, metadata, or knowledge-base content.
- `TargetAdapter` sends authorized black-box tests to a running RAG/chat application.
- `ModelProvider` supplies an optional analysis model for RAGScanner itself.

Using OpenAI, Hugging Face, or OpenWebUI does not prove that retrieval exists. A target is called a
RAG target only when document/vector/index retrieval is verified.

See [ARCHITECTURE.md](ARCHITECTURE.md), [PRODUCT.md](PRODUCT.md), and
[docs/status/current.md](docs/status/current.md) for the detailed boundaries and current status.

## Roadmap

The immediate sequence is:

1. Remaining persistence recovery and API-scale history/comparison work
2. Capability-tiered SharePoint, web, SaaS, Git, object-store, and vector connectors
3. OpenWebUI compatibility, incremental change detection, source identity, and secret providers
4. Dashboard scan detail, comparison, connector settings, and accessibility acceptance
5. Scheduler, retention, and notifications
6. Packaging and deployment hardening

Planned features are never presented as available. See [ROADMAP.md](ROADMAP.md) for details.

## Contributing and license

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing. Do not publish secrets, exploits, or
customer content in public issues.

RAGScanner is licensed under the [Apache License 2.0](LICENSE). There is one free, open-source
product: no Community/Pro split, paid rule feed, subscription, entitlement, or closed module.
