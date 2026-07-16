# Bring Your Own Model

Chat and embedding providers are independently configured behind capability-based interfaces.

## Available report enrichment

`ragscanner analyze-report` can append validated advisory analysis to an existing JSON report and
write a new JSON or standalone HTML artefact. It supports a loopback Ollama endpoint and a generic
OpenAI-compatible chat-completions endpoint. The scan itself remains deterministic: enrichment does
not alter scores, findings, evidence, or scan history.

Only a bounded summary of deterministic findings (ID, severity, title, impact, and recommendation)
is sent to the provider. Raw document text and finding evidence are excluded; common secret-like
values are redacted. Ollama defaults to `http://127.0.0.1:11434`. A non-loopback endpoint requires
`--consent-remote` and HTTPS. OpenAI-compatible endpoints also require a non-persisted `env:`
credential reference.

Example:

```console
ragscanner analyze-report report.json --provider ollama --model llama3.2 --output detailed-report.html
```

Planned adapters include local embeddings, an OpenWebUI model endpoint, NVIDIA NIM, vLLM, and
LiteLLM where they satisfy the compatibility contract.

## Defaults and consent

- Offline is the default; no API key and no chat call are required.
- Remote endpoints are never auto-enabled or inferred from ambient credentials.
- Configuration and preflight show endpoint, provider, model, locality, capabilities, and intended data classes.
- Balanced analysis sends only deterministic candidates and minimal relevant excerpts after known-secret and configured-PII redaction.
- Reports record provider/model, remote-use status, privacy settings, and failed/skipped model checks without storing credentials.

Provider output is untrusted and strictly validated. Timeouts, retries, budgets, context limits, TLS policy, rate limits, deterministic fake providers, and cancellation are part of the contract. “OpenAI-compatible” must be defined by tested endpoints/features, not assumed from branding.
