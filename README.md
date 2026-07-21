# RAGScanner

> Scan your RAG before your users do.

**English** · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner is a free, open-source, local-first scanner for security and content-quality risks in RAG
knowledge sources. It combines deterministic scanning, durable jobs, report history, recurring
monitoring, and optional advisory AI analysis in a machine-local dashboard.

> [!WARNING]
> RAGScanner is a technical alpha. A static report is a review aid, not proof that a running RAG
> system is secure or protected from every prompt-injection technique.

## Available now

| Area | Current capability |
|---|---|
| Local content | Single files and root-confined folders |
| Formats | Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB, RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML, and logs |
| Remote sources | OpenWebUI knowledge bases; HTTPS pages, documents, same-origin sitemaps, and accessible SharePoint URLs |
| Analysis | Static security rules, exact/lexical duplicate checks, and chunk-quality checks |
| Reports | Terminal, JSON, standalone HTML, and detailed dashboard reports |
| History | Readable IDs, filters, detail, comparison, health trends, and permanent deletion |
| Jobs | Durable one-time jobs, recurring intervals, cancellation, retry, progress, and safe logs |
| AI | Optional local or explicitly consented remote advisory analysis; off by default |
| Languages | English, Turkish, German, French, Simplified Chinese, and Italian dashboard labels |
| Installation | Machine-local Host Service on Windows, macOS, and Linux |

OCR, semantic duplicate analysis, authenticated Microsoft Graph library discovery, vector-store
content connectors, cron/calendar schedules, configurable retention, multi-user authentication,
and Docker deployment are not available yet. Detection of a platform is not content access or an
assessment.

## Install and open

Install from the official repository, then create the machine service:

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

The installer opens the local dashboard. Later, use:

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

Administrator permission is required for machine installation and lifecycle commands. The default
dashboard is loopback-only and is also available at `http://local.ragscanner.com` after installation.

## Update, repair, and uninstall

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update` installs the latest official `main` runtime and preserves settings, secrets, jobs, and
reports. `repair` rebuilds the runtime and service registration. `uninstall` preserves local data by
default; `--purge-data` permanently removes it.

## Scan content

The dashboard is the recommended interface. For automation or direct local scans:

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

The Create job drawer supports:

- local files and folders;
- OpenWebUI knowledge bases after explicit content consent;
- one HTTPS page or supported document;
- same-origin URL sitemaps and one nested sitemap-index level;
- directly accessible SharePoint URLs, with an optional bearer-token environment reference;
- one-time execution or recurring interval monitoring.

Remote web scans reject redirects and cross-origin sitemap entries, never execute scripts, and
apply page, response-size, and timeout limits. Authenticated Microsoft Graph site/library discovery
is a separate planned connector.

## AI-assisted reports

AI analysis is optional and does not replace deterministic findings. Settings discovers installed
models from Ollama, LM Studio, LocalAI, or vLLM instead of retaining a stale model name. Remote
providers require HTTPS, an external credential reference, and explicit per-scan consent.

Only a bounded, redacted finding summary is sent to the selected model—never raw documents or
finding evidence. Output is schema-validated. If a local compatible server rejects structured-output
fields with HTTP 400, RAGScanner retries once in JSON compatibility mode and records an actionable
error code if that also fails. Common schema drift is normalized, invented finding references are
discarded safely, and accepted analysis can attach remediation and verification steps to each real
finding.

## Reports and operations

Overview health always uses the latest remaining completed report. Reports can be filtered,
compared by date, inspected in detail, or permanently deleted after confirmation. One-time jobs and
recurring definitions are displayed separately. The Activity section shows stable success/failure
codes and safe reasons without raw provider responses or credentials. Recurring schedules expose
their next run time and interval for editing. Reports show security, content-quality, and efficiency
scores, file/page/line provenance, highlighted evidence, and the same score bands everywhere: below
85 yellow, below 70 orange, and below 55 red. AI analysis waits up to 180 seconds by default for
slower local models; provider errors and report UI data follow the selected dashboard language.

Useful operational commands include:

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

See the [complete CLI reference](docs/cli.md), [dashboard guide](docs/dashboard.md), and
[troubleshooting guide](docs/troubleshooting.md) for advanced options.

## Privacy and security

- Static local scans are offline by default and do not require an LLM.
- Remote document or model access requires visible configuration and explicit consent.
- API keys are stored outside SQLite in owner-readable machine files or external `env:` references.
- Durable jobs and reports contain only opaque secret references.
- Parsed content, model output, URLs, and report evidence are treated as untrusted and bounded.
- Product-generated UI labels are localized; source evidence remains in its original language.

Read [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md), and the
[source connector contract](docs/source-connector-contract.md) before exposing new integrations.

## For contributors

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

Before submitting changes, run Ruff, formatting, mypy, tests, and `uv build` as documented in
[CONTRIBUTING.md](CONTRIBUTING.md). Architecture boundaries are defined in
[ARCHITECTURE.md](ARCHITECTURE.md); current availability is tracked in
[docs/status/current.md](docs/status/current.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
