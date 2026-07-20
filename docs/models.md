# Models and providers

RAGScanner is designed not to require a chat model. Offline deterministic checks come first.
`ragscanner analyze-report` can enrich an exported report, while a direct scan or dashboard job can
opt in to the same bounded advisory analysis before its report snapshot is saved. AI output never
changes deterministic findings or scores. See [BYOM.md](../BYOM.md).

Reports identify provider/model and remote use, but never keys. The dashboard can accept an API key
stored outside SQLite in a protected owner-readable machine file, or an advanced `env:` reference;
durable jobs store only the opaque reference. These protected files live with preserved machine data,
so normal `ragscanner update` runtime replacement does not remove them. Provider failures preserve
the deterministic report and record a stable safe error code and message. Unsupported capabilities
are visible rather than silently downgraded.
