# RS-053: Generic OpenAI-compatible target adapter

**Objective:** Chat Completions tabanlı generic target için güvenli ilk network adapter’ı oluşturmak.  
**Rationale:** OpenAI, TGI, vLLM, LiteLLM, NIM ve birçok gateway ortak protokole yaklaşır.  
**Dependencies:** RS-046; OD-030.  
**Scope:** Base URL/model/auth reference, chat request/response, streaming off baseline, timeout, rate limit, response size ve capability config.  
**Out of scope:** Source/vector-store erişimi, ambient API key auto-enable, provider-specific core logic.  
**Implementation guidance:** Injected HTTP client ve mock transport; exact supported schema belgelenir.  
**Security considerations:** SSRF/DNS rebinding/redirect/TLS, key redaction, allowed hosts, request budget.  
**Acceptance criteria:** Mock contract geçer; ağ varsayılan kapalı; key hiçbir output/log’da yok; malformed cevap fail-safe.  
**Tests:** Success/401/429/timeout/redirect/private IP/malformed/oversized/stream cases.  
**Documentation changes:** Target configuration and compatibility tier.  
**Completion checklist:** [ ] SSRF policy [ ] Mock only CI [ ] Rate limit [ ] Redaction [ ] Docs updated

