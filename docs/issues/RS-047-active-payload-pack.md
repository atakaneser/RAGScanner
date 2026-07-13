# RS-047: Versioned active security payload pack

**Objective:** Prompt injection, leakage, function abuse ve context manipulation için sürümlü, çok dilli payload şeması oluşturmak.  
**Rationale:** Active testler tekrar üretilebilir ve risk profiline göre seçilebilir olmalıdır.  
**Dependencies:** RS-004, RS-046; OD-026.  
**Scope:** Payload ID/version/category, risk/non-destructive flag, prerequisites, expected signals, exclusions, references ve TR/EN fixture’lar.  
**Out of scope:** Payload gönderme, destructive tool çağrısı, fake vulnerability sonucu.  
**Implementation guidance:** YAML/JSON schema; varsayılan yalnız safe profile; custom pack validation.  
**Security considerations:** Payload hiçbir zaman local command olarak çalıştırılmaz; destructive içerik ikinci onay olmadan seçilmez.  
**Acceptance criteria:** Pack validation ve uniqueness; her payload’ın safe/refusal fixture’ı; version provenance.  
**Tests:** Schema, duplicate ID, malformed pack, multilingual boundary ve safe-profile selection.  
**Documentation changes:** Payload contribution and safety guide.  
**Completion checklist:** [x] Schema [x] Safe profile [x] TR/EN corpus [x] Malformed tests [x] Docs updated
