# Models and providers

RAGScanner is designed not to require a chat model. Offline deterministic checks and optional local embeddings come first. Balanced/Deep features may use separately configured chat and embedding providers only with explicit data-flow consent. See [BYOM.md](../BYOM.md).

Reports will identify provider/model and remote use, but never keys. Unsupported capabilities cause checks to be visibly skipped, not silently downgraded.

