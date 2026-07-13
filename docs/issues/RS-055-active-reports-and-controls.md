# RS-055: Active scan controls and safe reports

**Objective:** Active scan için terminal/JSON/HTML raporu, progress, delay/rate limit, budget ve cancellation eklemek.  
**Rationale:** Endpoint testleri operasyonel kontrol ve güvenli kanıt olmadan kullanılamaz.  
**Dependencies:** RS-048–054, RS-018/019.  
**Scope:** Per-test status, request count/duration, target/analyzer/payload versions, skipped/failed tests, redacted response evidence ve exit policy.  
**Out of scope:** Fake demo vulnerability, raw response dump, dashboard.  
**Implementation guidance:** Safe synthetic demo yalnız “fixture” etiketiyle; report DTO ortak finding modelini kullanır.  
**Security considerations:** HTML escape, secret/PII redaction, response retention, terminal control chars.  
**Acceptance criteria:** Report coverage ve failed checks görünür; fake fixture gerçek target olarak sunulmaz; cancellation tutarlı.  
**Tests:** Golden JSON, XSS, redaction, budget, cancel, partial failure ve deterministic ordering.  
**Documentation changes:** Active report schema and CLI guide.  
**Completion checklist:** [ ] Coverage [ ] Redaction [ ] No fake result [ ] Exit codes [ ] Docs updated

