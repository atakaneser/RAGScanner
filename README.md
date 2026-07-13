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
| English guided onboarding | Available with bare `ragscanner` |
| Consent-based container OpenWebUI discovery and KB/file metadata inventory | Available |
| OCR and semantic duplicate analysis | Not available yet |
| Opt-in SQLite history and coverage-aware comparison | Available from the CLI |
| Localhost history API | Available with `ragscanner serve` |
| Durable SQLite static-scan jobs and worker | Available |
| Scoped authenticated asynchronous scan/job API | Available on loopback |
| Local overview and queue dashboard | Available with `ragscanner serve` |
| Consent-gated OpenWebUI knowledge content connector | Available |
| Scheduler and vector-store content connectors | Not available yet |
| ModelProvider/BYOM integration | Not available yet |
| Active endpoint scan CLI | Not available; core contracts only |

`ragscanner scan` runs the local discovery → parsing → normalization → chunking → static security
→ duplicate analysis → chunk quality → scoring → reporting pipeline.

## Quick start for users

Requirements: Python 3.12 or 3.13 and [`uv`](https://docs.astral.sh/uv/).

Install the alpha directly from GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

The bare command opens an English onboarding flow. It asks which source you use, suggests bounded
nearby local sources, and can start a scan. After explicit consent, OpenWebUI discovery inspects
bounded metadata from available Docker, Podman, nerdctl, or Finch runtimes plus common loopback
addresses. A separately supplied in-memory API key can inventory accessible knowledge bases plus
knowledge-linked and standalone/chat files. A separate explicit-consent job can retrieve accessible
files from one selected OpenWebUI knowledge base and run the static pipeline.

Maintain or remove the installation with one RAGScanner command:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

`uninstall` asks for confirmation. Automation may use `ragscanner uninstall --yes`. These commands
delegate to the official `uv tool` environment without a shell; `repair` performs a full reinstall
while retaining the original installation source and settings.

After a PyPI release, installation will use `uv tool install ragscanner`. No PyPI package or release
tag has been published yet.

## Direct scans

Use quotes around paths containing spaces, parentheses, or other shell-sensitive characters.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Create reports:

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
- Document or chunk content is not sent to external AI services.
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
