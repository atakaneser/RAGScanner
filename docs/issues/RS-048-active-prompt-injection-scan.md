# RS-048: Active prompt-injection scan

**Objective:** Yetkili target’ta prompt injection, jailbreak, role manipulation ve system prompt extraction davranışını test etmek.  
**Rationale:** Static belge taraması çalışan uygulamanın talimat hiyerarşisini doğrulayamaz.  
**Dependencies:** RS-046/047/052/053.  
**Scope:** Non-destructive payload execution, per-test status, refusal/suspected/confirmed semantics ve finding provenance.  
**Out of scope:** Tool side effects, kaynak belge tarama, otomatik exploit.  
**Implementation guidance:** Tek payload sonucu değil, kontrollü baseline/attack karşılaştırması kullan.  
**Security considerations:** Explicit authorization, budget/rate limit, response redaction, no system prompt storage by default.  
**Acceptance criteria:** Vulnerable/safe/refusal/ambiguous fixtures doğru sınıflanır; hata vulnerability sayılmaz.  
**Tests:** TP/FP/boundary, timeout, retry, multilingual ve prompt-refusal regression.  
**Documentation changes:** Active scan usage/limitations.  
**Completion checklist:** [ ] Authorization gate [ ] Baseline [ ] TP/FP [ ] Provenance [ ] Docs updated

