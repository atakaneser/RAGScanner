# RS-052: Deterministic active response analyzer

**Objective:** Target cevaplarını broad keyword eşleşmesine dayanmadan açıklanabilir şekilde sınıflandırmak.  
**Rationale:** “system”, “API” veya uzun cevap gibi sinyaller tek başına ciddi false positive üretir.  
**Dependencies:** RS-004/047; OD-029.  
**Scope:** Baseline delta, exact canary, structured tool events, refusal, indicator combination, confidence ve coverage.  
**Out of scope:** Zorunlu LLM judge, tek regex ile confirmed finding.  
**Implementation guidance:** Deterministic first; confirmed/suspected/inconclusive ayrı; analyzer version raporda.  
**Security considerations:** Response untrusted; escape/redact/truncate; regex/resource limits.  
**Acceptance criteria:** Labeled fixture metrikleri onaylı eşiği karşılar; error/timeout vulnerability değildir.  
**Tests:** TP/FP, refusal, ambiguous, multilingual, XSS, secrets ve oversized/streaming response.  
**Documentation changes:** Classification and confidence methodology.  
**Completion checklist:** [ ] Labeled corpus [ ] Baseline delta [ ] Redaction [ ] Metrics [ ] Docs updated

