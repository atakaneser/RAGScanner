# OpenWebUI integration

The OpenWebUI integration is planned but not implemented. The current bare CLI can perform bounded
loopback health-candidate discovery only after explicit consent; it does not retrieve content and
does not prove that a responding service is OpenWebUI.

OpenWebUI document-source, active-target, and optional model-provider roles will use separate
configurations. Core will not depend on OpenWebUI SDK/API types. Credential values will not be
logged, persisted as plain text, or sent to the browser. RS-028 covers endpoint validation, SSRF,
timeout, response-size, permission, pagination, and supported-version behavior.

Production knowledge/model discovery, content retrieval, synchronization, and OpenWebUI scan
commands are not available yet.
