# Models and providers

RAGScanner is designed not to require a chat model. Offline deterministic checks and optional local embeddings come first. `ragscanner analyze-report` is an opt-in post-processing command: it can use a loopback Ollama model or an explicitly consented HTTPS OpenAI-compatible endpoint to produce validated advisory sections in a new report artefact. It never changes deterministic scan results or stored scan history. See [BYOM.md](../BYOM.md).

Reports will identify provider/model and remote use, but never keys. Unsupported capabilities cause checks to be visibly skipped, not silently downgraded.
