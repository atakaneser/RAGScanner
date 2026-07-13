# Security policy

## Current status

The repository contains Core contracts, active-security components, a local ingestion pipeline, and
the first deterministic static RAG Security Scan engine. API, dashboard, persistence, and worker are
not implemented. No current feature provides complete protection or a security guarantee.

## Project-wide rules

- Never commit or publish real secrets, customer documents, production reports, private endpoints,
  or personal data.
- `.env.example` contains inert values; real `.env` files are ignored.
- Local static scans and `ragscanner doctor` perform no remote model, telemetry, or hidden network
  call.
- Domain and source metadata reject raw credential serialization and accept only opaque references.
- Inputs, parser/connector/model output, evidence, and browser-rendered values are untrusted.
- Tests and CI use synthetic fixtures and no real cloud credential.

## Active scanning

Active Scan requires explicit target-owner authorization and defaults to non-destructive `safe`
tests. Target adapters enforce allowed-host/SSRF policy, TLS, redirect rules, timeout, rate limits,
request/token/error budgets, cancellation, bounded responses, and credential references. Tool tests
use canary, simulated, dry-run, or no-op actions. Disabling safe mode never auto-enables destructive
payloads.

Target responses are escaped, truncated, and redacted before reporting. Keyword matches alone do
not produce confirmed vulnerabilities. Evaluation keeps `confirmed`, `probable`, `ambiguous`, and
`not_detected` distinct; transport errors remain failed/skipped tests.

The active test library contains reviewed declarative data only. It rejects real targets/contact
values, credential-like content, destructive commands/SQL, unknown placeholders, and unsafe payloads
mislabelled as safe. Loading a test never executes it.

## Network adapters

Generic REST uses explicit host/port allowlists, DNS address classification, private-network opt-in,
TLS by default, bounded streaming, and manually validated redirects. Metadata, loopback, and
link-local destinations are blocked unless a narrowly authorized policy allows them. Cross-host
credential redirects are blocked. DNS validation cannot fully eliminate the rebinding window and
that limitation remains documented.

## Files and parsers

The filesystem connector is confined to an explicit absolute non-root directory. Traversal,
external symlinks, special files, and uncontrolled discovery/read sizes fail closed. Symlinks are
off by default. TOCTOU risk is reduced with descriptor checks but cannot be eliminated.

PDF parsing operates on bounded memory, executes no JavaScript/action, follows no link, extracts no
attachment, and rejects encryption. Page/text/metadata/time limits apply. Image-only files produce
an OCR-needed warning; OCR is not implemented. Native calls use cooperative rather than process-level
preemption.

DOCX parsing preflights ZIP entry count, decompressed size, XML parts, compression ratio, unsafe
paths, and encryption. XML uses an entity-safe parser. Macros, OLE/embedded objects, comments,
tracked changes, hidden text, and external relationships are reported as signals; nothing is
executed, extracted, rendered, or fetched.

## Normalization and chunking

Normalization is not sanitization. Original content is not mutated. Multilingual text is preserved
with NFC default; invisible/control characters remain auditable through deterministic markers,
warnings, and annotations. Markdown/code/table/preformatted whitespace is treated conservatively.
PDF repair never crosses page, heading, list, table, URL/path, or code boundaries. Boilerplate is
only marked as a candidate.

Chunking validates document identity and normalization hash, never summarizes or deletes suspicious
text, and reports hard structural splits. Input, token, block, chunk, overlap, character, metadata,
and mapping limits are explicit. It performs no network, embedding, LLM, rendering, or content log.

## Rules and analysis

Static rules are reviewed declarative JSON executed by restricted matchers. Arbitrary Python, shell,
templates, and unsafe regex constructs are rejected. Base64/ROT13/Unicode/hex decoding is strictly
bounded and decoded content is never executed. URLs are parsed but not fetched. Evidence is bounded,
escaped, and secret-masked. PII detection is off by default and pattern matches are not proof of
identity.

Duplicate and chunk-quality analysis is local and read-only. Canonical duplicate members are report
references, not automatic deletion decisions. Lexical near duplicates do not prove semantic
equivalence and require review. Limits produce structured warnings rather than hidden omissions.

## Reports and persistence boundary

Reporting performs final-boundary redaction for private keys, connection strings, bearer/API keys,
cookies, credential URLs, and sensitive fields. Absolute paths are hidden by default. HTML escapes
dynamic values, creates no links from source URLs, embeds no source documents, loads no external
asset, and uses a restrictive CSP. Limit exhaustion is explicit.

Future storage will persist secret references only. Raw content/artifacts remain local and subject to
an explicit retention policy before persistence is considered complete.

## Reporting a vulnerability

Do not open a public issue. Create a private draft through
[GitHub Security Advisories](https://github.com/atakaneser/RAGScanner/security/advisories/new).
Do not attach real secrets, customer documents, production reports, or unnecessary exploit data to
issues, discussions, or pull requests.

There is no stable release. Security fixes for technical alpha `0.1.0a1` are best effort; old alpha
snapshots have no backport guarantee.
