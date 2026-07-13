# RS-049: Active data-leakage scan

**Objective:** Context, cross-session, secret/PII ve knowledge-base disclosure davranışlarını güvenli test etmek.  
**Rationale:** Leakage ancak hedef cevabı ve yetkili sentetik canary’lerle güvenilir ölçülebilir.  
**Dependencies:** RS-046/047/052.  
**Scope:** Synthetic canary, context enumeration, prior-session probes, redacted evidence ve confidence.  
**Out of scope:** Gerçek müşteri verisi toplama, training-data extraction iddiası, tenant SaaS kurulumu.  
**Implementation guidance:** Bilinen sentetik canary olmadan broad keyword eşleşmesini confirmed yapma.  
**Security considerations:** Response retention/minimization; gerçek secret/PII raporda maskelenir.  
**Acceptance criteria:** Canary leakage yakalanır; normal güvenli cevap ve dokümantasyon false positive olmaz.  
**Tests:** Canary TP, refusal FP, PII redaction, cross-session isolation fake ve oversized response.  
**Documentation changes:** Leakage methodology and legal warning.  
**Completion checklist:** [ ] Canary model [ ] Redaction [ ] TP/FP [ ] No real data [ ] Docs updated

