# Privacy principles

This is an engineering privacy design, not a published legal privacy notice.

- Local execution and no remote model calls are the defaults.
- RAGScanner Cloud must not receive raw document content by default.
- Remote-model use is opt-in per configuration, with visible endpoint/model, data minimization, secret redaction, configurable PII redaction, and report provenance.
- Chat and embedding providers have separate configurations and consent/data-flow descriptions.
- Store the least evidence needed; make evidence bounds and raw-content retention configurable.
- Avoid full document content in logs, analytics, error tracking, notifications, and support bundles.
- Define purpose, retention, deletion, export, residency, subprocessors, backups, and breach handling before collecting account or scan metadata.
- Account deletion, if accounts are enabled, must address active jobs, credentials, artifacts, audit/legal retention, and backups transparently.
- Telemetry must be documented, privacy-conscious, and optional where feasible.

Open decisions include optional hosted-service data maps, default retention periods, PII detector regions/policies, analytics policy, support access, and data residency. The default product remains local/self-hosted.
