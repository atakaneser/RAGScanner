# OpenWebUI integration

The OpenWebUI content integration is available as a technical-alpha, read-only source connector.
After explicit consent, the bare CLI can inspect bounded running-container metadata through Docker,
Podman, nerdctl, or Finch CLIs and probe only resulting/common loopback health endpoints. With
separate consent, a user-supplied API key held only in memory can inventory accessible knowledge
bases and linked or standalone/chat file metadata through bounded pagination. Production scan jobs
select one knowledge base and separately authorize bounded content retrieval.

OpenWebUI document-source, active-target, and optional model-provider roles use separate
configurations. Core does not depend on OpenWebUI SDK/API types. Credential values are not logged,
persisted as plain text, or sent to the browser. The source connector enforces endpoint validation,
HTTPS outside loopback, no redirects or environment proxies, timeouts, response-size limits,
permissions, and pagination.

Knowledge-linked document retrieval and OpenWebUI scan jobs are available. Incremental
synchronization, standalone/chat-file selection for content scans, model discovery, and OpenWebUI
target testing are not available yet.
