# RS-046: TargetAdapter contract

**Objective:** Çalışan RAG/chat endpoint’lerine active test göndermek için vendor-neutral capability, request, response ve error sözleşmelerini oluşturmak.  
**Rationale:** OpenAI, TGI, OpenWebUI ve custom REST desteği core’da vendor dalları üretmemelidir.  
**Dependencies:** RS-004 core models; ADR-0011; OD-027.  
**Scope:** Healthcheck, capability discovery, send-test, session/correlation, bounded response, timeout/cancel ve provenance modelleri.  
**Out of scope:** HTTP adapter, payload corpus, gerçek network çağrısı.  
**Implementation guidance:** Protocol/ABC ve deterministic fake adapter; source/model rollerinden ayrı config kimliği.  
**Security considerations:** Credential repr/redaction, allowed-host metadata ve side-effect capability zorunlu alanlar.  
**Acceptance criteria:** Fake adapter contract testleri; vendor import yok; response streaming/partial/error temsil edilir.  
**Tests:** Unit/property, cancellation, malformed/oversized response ve serialization golden files.  
**Documentation changes:** Architecture, SDK ve compatibility contract.  
**Completion checklist:** [ ] Contract reviewed [ ] Fake adapter [ ] No network [ ] Type tests [ ] Docs updated

