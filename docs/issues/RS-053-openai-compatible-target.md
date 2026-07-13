# RS-053: Generic OpenAI-compatible target adapter

**Objective:** Implement the first safe network adapter for a generic Chat Completions target.
**Rationale:** OpenAI, TGI, vLLM, LiteLLM, NIM, and many gateways approximate a shared protocol.
**Dependencies:** RS-046; OD-030.
**Scope:** Base URL/model/auth reference, chat request/response, non-streaming baseline, timeout, rate limit, size limit, and capability configuration.
**Out of scope:** Source/vector-store access, ambient-key auto-enable, and provider branches in Core.
**Implementation guidance:** Inject HTTP client and mock transport; document the exact supported schema.
**Security:** SSRF/DNS rebinding/redirect/TLS controls, key redaction, allowed hosts, and request budget.
**Acceptance:** Mock contract passes; network defaults off; keys never appear in output/logs; malformed responses fail safely.
**Tests:** Success, 401, 429, timeout, redirect, private IP, malformed, oversized, and streaming cases.
**Documentation:** Target configuration and compatibility tier.
**Checklist:** [ ] SSRF policy [ ] Mock-only CI [ ] Rate limit [ ] Redaction [ ] Docs updated
