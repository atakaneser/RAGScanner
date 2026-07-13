# RS-022: OpenAI-compatible provider adapter

**Objective:** Implement an explicit, tested chat/embedding endpoint adapter without vendor lock-in.  
**Rationale:** Many BYOM endpoints expose related APIs, but compatibility varies.  
**Dependencies:** RS-004, provider contract/RS-024; OD-013.  
**Scope:** Base URL/model/auth references, capability detection/config, timeouts/retries/cancellation, structured output validation, token/budget accounting, provenance.  
**Out of scope:** Enabling remote use by default, storing keys, guaranteeing every “compatible” product.  
**Implementation guidance:** Define supported endpoints/features; separate chat/embedding instances; inject HTTP client; classify retryable errors.  
**Security considerations:** SSRF/base-URL policy, TLS, proxy behavior, key redaction, response size/schema, minimal redacted excerpts, prompt injection isolation.  
**Acceptance criteria:** Contract tests against deterministic stub; explicit consent required; no secret in logs/errors; unsupported capabilities fail visibly.  
**Tests:** Stub integration, auth redaction, timeout/retry/cancel, malformed/hostile JSON, oversized response, SSRF policy, no-network default.  
**Documentation changes:** BYOM, models/configuration/privacy/troubleshooting.  
**Completion checklist:** [ ] Compatibility defined [ ] Consent tested [ ] SSRF review [ ] Fake CI only [ ] Docs updated

