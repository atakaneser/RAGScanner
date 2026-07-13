# Domain models

`ragscanner.domain` uses Pydantic and imports no FastAPI, SQLAlchemy, Typer, HTTP client, filesystem,
database, or UI framework.

- `SourceLocation` identifies source, path, page, section, lines, and metadata.
- `Document` preserves original/normalized content, hash, MIME/language, aware times, metadata, and
  warnings.
- `Chunk` preserves document/index identity, original/normalized text, hashes/counts, source,
  headings, ranges, and provenance.

Normalization models describe conservative configuration, result hashes/content, source-mapping
segments, warnings, annotations, statistics, and version. Chunking models describe strategy,
resource limits, warnings, statistics, algorithm/tokenizer versions, and complete configuration
identity. Neither stage mutates the input document.

Static and active observations share `Finding`. Static findings identify source/document/chunk;
active findings require target/test-case/execution together. Severity (impact), confidence (evidence
strength), and classification (confirmed/probable/ambiguous/not-detected/inconclusive) remain
separate. High severity does not imply confirmation; not-detected is not a guarantee.

Scan types are static, active, and combined; analysis modes are offline, balanced, and deep;
lifecycle states are pending, running, completed, completed-with-warnings, failed, and cancelled.
Active/combined scans require a valid non-expired authorization scope and target. Safety defaults to
safe. Score fields are 0–100 or `None` for not-assessed.

Unified pipeline contracts hold configuration, results, source health, documents/chunks, findings,
groups, statistics, warnings/errors/skips, scores, cancellation, and provider-neutral events.

Fingerprints are SHA-256 over canonical versioned JSON. Document hash depends on content; chunk
identity depends on source/document/index/normalized content plus algorithm configuration; finding
identity depends on rule, location/target, and evidence. Namespace version changes whenever the
algorithm changes. Mutable fields use factories and all domain datetimes must be timezone-aware.
