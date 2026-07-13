# Agent guide

RAGScanner is currently in Milestone 0: product foundation. Read `README.md`, `PRODUCT.md`, `ARCHITECTURE.md`, and `docs/status/current.md` before changing scope.

- Keep Core independent of UIs, connectors, databases, model vendors, and MCP.
- Preserve local-first defaults: no remote document transmission or model use without explicit consent.
- Do not claim planned features are available. Update status and documentation with every change.
- Never commit secrets or raw customer content. Treat parsed files, model output, and report evidence as untrusted.
- Add tests for every implementation change and follow the checks documented in `CONTRIBUTING.md`.
- Use feature branches and conventional commits. Do not commit, push, publish, or change remotes without explicit approval.
- Record durable architectural choices as ADRs in `docs/decisions/`; record unresolved choices in `PLANS.md`.
- After every repository content change, refresh the existing Graphify knowledge graph with
  `graphify update .` (equivalent to `/graphify . --update`) before reporting completion. Treat a
  Graphify refresh failure as a visible completion warning, not as permission to hide or discard
  the underlying implementation change.
