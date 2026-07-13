# Bring Your Own Model

Chat and embedding providers are independently configured behind capability-based interfaces. Planned adapters include local embeddings, Ollama, an OpenWebUI model endpoint, OpenAI-compatible APIs, NVIDIA NIM, vLLM, and LiteLLM where they satisfy the compatibility contract.

## Defaults and consent

- Offline is the default; no API key and no chat call are required.
- Remote endpoints are never auto-enabled or inferred from ambient credentials.
- Configuration and preflight show endpoint, provider, model, locality, capabilities, and intended data classes.
- Balanced analysis sends only deterministic candidates and minimal relevant excerpts after known-secret and configured-PII redaction.
- Reports record provider/model, remote-use status, privacy settings, and failed/skipped model checks without storing credentials.

Provider output is untrusted and strictly validated. Timeouts, retries, budgets, context limits, TLS policy, rate limits, deterministic fake providers, and cancellation are part of the contract. “OpenAI-compatible” must be defined by tested endpoints/features, not assumed from branding.

