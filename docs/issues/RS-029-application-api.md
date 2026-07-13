# RS-029: Application API

**Objective:** Expose versioned authenticated scan/knowledge-base/result contracts without leaking core internals.  
**Rationale:** Connectors, agents, and future dashboard need a stable service boundary.  
**Dependencies:** RS-004, RS-018, job contract; ADR-0002/0007/0021.
**Scope:** API framework decision, OpenAPI, API-key auth for connector use, create/status/result scan endpoints, pagination/errors/idempotency/rate limits.  
**Out of scope:** Browser account auth, dashboard, and scheduler technology.  
**Implementation guidance:** Thin delivery layer over application services; generated client contract; asynchronous scans; explicit API/schema versions.  
**Security considerations:** Authz every resource, hashed/scoped/rotatable keys, tenant context, request/body limits, SSRF/source validation, audit/redaction.  
**Acceptance criteria:** Contract supports connector manual scan; idempotent create; consistent errors; unauthorized/cross-tenant access denied without existence leaks.  
**Tests:** Unit/integration/OpenAPI, auth scope/rotation, tenant isolation, rate/body limits, idempotency, malformed/hostile payloads.  
**Documentation changes:** API reference, integration/config/security.  
**Completion checklist:** [x] Local read-only threat boundary [x] Initial versioned OpenAPI
[x] Stable error envelope [x] Read/write contract tests [x] Scoped API-key auth [x] Async scan creation
[x] Durable job contract [x] Idempotency/rate limits [x] Initial scope matrix [ ] Tenant isolation
[ ] Generated client stability [x] Initial docs
