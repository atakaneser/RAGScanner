# SourceConnector contract

`SourceConnector` is a vendor-neutral read-only async port for source inventory, content, and change
information. Filesystem, OpenWebUI, vector database, or object-store implementations are adapters,
not Core.

It is distinct from TargetAdapter and ModelProvider. Static and active scanning are separate, and an
LLM endpoint alone is not proof of RAG retrieval. Concrete connectors must propagate cancellation,
enforce time/resource limits, and honor the mandatory `get_content(..., max_bytes)` budget by safe
failure or explicit truncation.

Contracts include descriptor/capabilities, inventory items, bounded content, opaque cursors,
add/modify/delete/unchanged/unknown changes, health status, typed pages, and structured errors.
Messages, representations, logs, and reports must contain no credential or source content. Secret
configuration uses opaque references only; cursors return to the connector without inspection.

`FakeSourceConnector` is deterministic in-memory test support with no network/filesystem access.
