# Reporting engine

RAGScanner produces framework-independent, fully offline reports from static, active, or combined
scan results. Reporting does not depend on persistence, FastAPI, or dashboard models. `ReportInput`
combines scan, finding, execution, score, duplicate, chunk-quality, ingestion, and scanner data;
`ReportBuilder` creates a redacted immutable view.

The unified `ragscanner scan` pipeline uses the same terminal, JSON, and HTML reporters without a
database or fake result. Each report contains the knowledge-base mode, source count, per-assessment
coverage, and per-file ingestion issues. A `not_assessed` check is never presented as healthy or as
a zero score, and its reason remains visible.

The default terminal view is deliberately concise: scan outcome, discovered/processed/skipped file
counts, high-priority security counts, and ingestion remediation. `--verbose` adds scores, findings,
coverage, evidence, and technical diagnostics.

HTML begins with an executive summary and file-ingestion table. Scores are explicitly limited to
assessed checks and never claim a security guarantee. Configuration and scan identifiers live under
technical details rather than dominating the first view.

Finding order is deterministic: severity, classification, confidence, category, source, rule ID,
and fingerprint. Severity, confidence, and classification remain separate. Missing scores are
`null`/`Not assessed`; estimated token or character savings are labeled as estimates.

Dashboard PDF downloads group identical rule/remediation occurrences, repeat the shared impact and
recommendation once, and print at most 20 locations per group. The omitted count is explicit; HTML
and Excel downloads preserve the complete finding list for audit and filtering.

Report-time filters support severity, category, classification, document, target, rule ID,
informational inclusion, and maximum findings. Filters never mutate source results and truncation is
always reported.

Evidence, metadata, credential-like headers, URLs, connection strings, API keys, cookies, and
private keys are masked again at the report boundary. Absolute source paths default to basenames.
Suspicious URLs are not linked. Reporting performs no network, subprocess, analytics, or telemetry.

```bash
ragscanner report input.json --format terminal --verbose
ragscanner report input.json --format json --output report.json
ragscanner report input.json --format html --output report.html
```

Signed or verified reports remain unresolved under OD-016.
