# RS-057: Generic REST target adapter

**Objective:** Yapılandırılmış request/response mapping ile ilk concrete `TargetAdapter`ı uygulamak.  
**Rationale:** Custom RAG uygulamaları OpenAI şemasını kullanmayabilir; generic REST sonraki platform adapter’larının transport temelidir.  
**Dependencies:** RS-046; ADR-0013/0014.  
**Scope:** Allowed base URL, method/path, JSON request template alan eşleme, response text/tool/citation mapping, healthcheck, timeout/rate/budget/cancel.  
**Out of scope:** Arbitrary template code, shell/plugin execution, payload corpus ve vulnerability evaluation.  
**Implementation guidance:** Declarative bounded schema; injected HTTP transport; redirect kapalı; capability açık yapılandırma.  
**Security considerations:** Target-owner authorization, SSRF/DNS rebinding/TLS, secret reference, size limit ve safe mode.  
**Acceptance criteria:** Mock endpoint contract geçer; private/redirect/oversized/malformed hedef fail-safe; credential output’ta yok.  
**Tests:** Success, 4xx/5xx, timeout, cancel, 429, redirect, private IP, malformed/oversized JSON ve redaction.  
**Documentation changes:** Generic target configuration, supported mapping ve riskler.  
**Completion checklist:** [ ] Authorization [ ] SSRF controls [ ] Mock tests [ ] No custom code [ ] Docs updated

