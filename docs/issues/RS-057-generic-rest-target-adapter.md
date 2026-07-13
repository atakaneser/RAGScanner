# RS-057: Generic REST target adapter

**Objective:** Implement the first concrete `TargetAdapter` with configured request/response mapping.
**Rationale:** Custom RAG applications may not use the OpenAI schema; Generic REST is the transport basis for later adapters.
**Dependencies:** RS-046; ADR-0013/0014.
**Scope:** Allowed URL, method/path, bounded JSON template mapping, response text/tool/citation mapping, health, timeout/rate/budget/cancel.
**Out of scope:** Arbitrary template code, shell/plugin execution, payload corpus, and vulnerability evaluation.
**Implementation guidance:** Declarative bounded schema; injected transport; redirects off; explicit capabilities.
**Security:** Target-owner authorization, SSRF/DNS rebinding/TLS, secret references, size limits, and safe mode.
**Acceptance:** Mock contract passes; private/redirect/oversized/malformed targets fail safely; credentials never appear in output.
**Tests:** Success, 4xx/5xx, timeout, cancel, 429, redirect, private IP, malformed/oversized JSON, and redaction.
**Documentation:** Generic target configuration, mapping, and risks.
**Checklist:** [ ] Authorization [ ] SSRF controls [ ] Mock tests [ ] No custom code [ ] Docs updated
