# Models and providers

RAGScanner is designed not to require a chat model. Offline deterministic checks come first.
`ragscanner analyze-report` can enrich an exported report, while a direct scan or dashboard job can
opt in to the same bounded advisory analysis before its report snapshot is saved. AI output never
changes deterministic findings or scores. See [BYOM.md](../BYOM.md).

Reports identify provider/model and remote use, but never keys. The dashboard can accept an API key
for the running Host Service process or an advanced `env:` reference; durable jobs store only the
generated reference. Provider failures preserve the deterministic report and record a stable safe
error code and message. Unsupported capabilities are visible rather than silently downgraded.
