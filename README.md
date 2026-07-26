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
| Analysis | Static security rules, exact/lexical duplicate checks, chunk-quality checks, and workload-aware RAG configuration advice |
| Reports | Terminal/JSON plus localized dashboard downloads in standalone HTML, Excel, and PDF |
| History | Readable IDs, filters, detail, comparison, health trends, and permanent deletion |
| Jobs | Durable one-time jobs, recurring intervals, cancellation, retry, progress, and safe logs |
| AI | Optional local or explicitly consented remote advisory analysis; off by default |
| Languages | English, Turkish, German, French, Simplified Chinese, and Italian dashboard labels |
| Installation | Machine-local Host Service on Windows, macOS, and Linux |

OCR, semantic duplicate analysis, authenticated Microsoft Graph library discovery, vector-store
content connectors, cron/calendar schedules, configurable retention, multi-user authentication,
and Docker deployment are not available yet. Detection of a platform is not content access or an
assessment.

Source and job forms deliberately list only the implemented content paths above. A vector database
cannot be assessed from its product or container name: a real connector must enumerate authorized
collections and read bounded payload text with document/chunk provenance. No accepted vector-store
connector exists yet, so Qdrant, Chroma, Weaviate, Milvus, pgvector, and similar platforms are not
offered as scannable sources.

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
dashboard has one fixed address: `http://localhost:8765`. It binds only to `127.0.0.1`, never edits
the hosts file, and does not accept a custom public hostname or port. Change the local administrator
password from Settings; doing so closes every other signed-in dashboard session.

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

Job creation is a four-step guided flow: choose a connected or manual source, enter only that
source's details, select one-time or recurring timing, choose a RAG workload, and optionally enable AI. Recurring jobs accept
an explicit first local date and time. Local AI providers are checked automatically; verified models
appear in one selector, while endpoint, credentials, and manual model entry stay under optional
connection controls.

## RAG configuration and validation

Every new report records the selected workload profile and compares the configured chunking with
observed chunk statistics. It recommends an explainable starting range for factual lookup, general
question answering, policies/procedures, long-context research, code, or tables, plus overlap and
initial retrieval top-k. There is no universal best chunk size; the report always lists the retrieval,
answer, citation, latency, and cost metrics required for representative-query validation.
The report summary links directly to these values. Duplicate findings separately compare both
bounded excerpts with source, page, line range, match type, and similarity; a stable reference is
never an automatic keep/delete decision.

Use `--rag-profile` and the optional model context/top-k flags on direct or queued CLI scans, or set
the `[rag]` table in `ragscanner.toml`. See [RAG configuration advice](docs/rag-configuration-advice.md).
Rule authors can measure a labelled local corpus with `ragscanner quality calibrate`; see
[Quality calibration](docs/quality-calibration.md). The bundled six-language corpus is a regression
smoke test, not evidence of production accuracy.

Remote web scans reject redirects and cross-origin sitemap entries, never execute scripts, and
apply page, response-size, and timeout limits. Authenticated Microsoft Graph site/library discovery
is a separate planned connector.

## AI-assisted reports

AI analysis is optional and does not replace deterministic findings. Settings discovers installed
models from Ollama, LM Studio, LocalAI, or vLLM instead of retaining a stale model name. Remote
providers require HTTPS, an external credential reference, and explicit per-scan consent.

Only bounded, secret-masked report context is sent to the selected model—never a raw document.
The context has a global 18,000-character limit and selects groups by highest severity, then affected
chunk count. Each selected group includes at most four evidence rows with source/page/line
provenance and a truncated snippet; the complete affected-chunk count remains explicit. The
advisory coverage caveat states how many lower-priority groups remain in the exhaustive deterministic
report. Raw evidence is omitted for static-security findings and every other finding from the same
affected source, while rule, file/page/line, impact, and deterministic remediation remain available.
This prevents document instructions from becoming advisory-model instructions.

The primary output must match the versioned JSON schema. RAGScanner accepts one unambiguous analysis
object from common local-model wrappers such as a JSON fence, reasoning prefix, or serialized JSON
string. If that response is invalid, one compact recovery request uses at most 6,500 characters, no
evidence snippets, and plain text instead of asking the same model for JSON again. RAGScanner wraps
usable recovery text in its own validated result envelope. Empty, malformed, wrong-language, or
severity-contradicting recovery text becomes a localized summary derived only from verified report
facts, with the limitation shown in the report rather than a terminal `ai_output_invalid`.
Compatible primary requests use JSON mode with temperature `0.1`; Ollama reserves a 16,384-token
context window. Detailed group actions are accepted only from the structured response and attach
only to real findings whose rule IDs they address.

## Reports and operations

Overview health always uses the latest remaining completed report. Reports can be filtered,
compared by date, inspected in detail, or permanently deleted after confirmation. One-time jobs and
recurring definitions are displayed separately. The Activity section shows stable success/failure
codes and safe reasons without raw provider responses or credentials. Recurring schedules expose
their next run time and interval for editing. Reports show security, content-quality, and efficiency
scores, file/page/line provenance, highlighted evidence, and the same score bands everywhere: below
85 yellow, below 70 orange, and below 55 red. AI analysis waits up to 180 seconds by default for
slower local models; provider errors and report UI data follow the selected dashboard language.
Exact duplicate groups show the normalized matching content and every retained location. Lexical
matches repeated inside one file are reported separately as ingestion/synchronization/chunk-overlap
diagnostics instead of appearing as unexplained cross-document duplicates.
Every saved report can be downloaded from its detail page as a network-free standalone HTML file,
a structured multi-sheet Excel workbook, or a paginated PDF. Exports use the selected interface
language while preserving source evidence in its original language.
New scans preserve source punctuation such as apostrophes in dashboard and PDF evidence. Naturally
short single-document answers and normalization-only offset approximations are not reported as
chunk defects.
Variation tests also prevent generated headings, lists, tables, code, overlap, uncased scripts, and
small lexical samples from creating findings without source-owned evidence.

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
