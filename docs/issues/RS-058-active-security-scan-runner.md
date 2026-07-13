# RS-058: Active Security Scan runner

**Objective:** Safe test-case pack, TargetAdapter ve response evaluator’ı idempotent active scan lifecycle’ında orkestre etmek.  
**Rationale:** Adapter tek başına scan değildir; authorization, progress, budget, cancellation ve coverage ortak runner’da uygulanmalıdır.  
**Dependencies:** RS-046/047/057/053/052; ADR-0012/0013.  
**Scope:** Authorization acknowledgement, safe profile default, test selection, baseline/attack sequence, progress, request/token budget, cancel, per-test result ve finding occurrence.  
**Out of scope:** Destructive payload, dashboard, scheduler, static document analysis.  
**Implementation guidance:** Pure orchestration + fake target/evaluator; target capability’ye uymayan test `skipped/not_assessed`.  
**Security considerations:** Safe mode kapatılsa bile destructive test otomatik açılmaz; tool testleri canary/no-op; credential yalnız secret reference.  
**Acceptance criteria:** Yetkisiz scan başlamaz; budget/cancel kesin uygulanır; sonuç confirmed/probable/ambiguous/not_detected ayrımını korur.  
**Tests:** Authorization, safe profile, canary tool, cancel, budget, timeout, partial failure, idempotency ve no-destructive regression.  
**Documentation changes:** Active scan lifecycle, CLI UX ve authorization warning.  
**Completion checklist:** [ ] Safe default [ ] Authorization gate [ ] Budget/cancel [ ] Result states [ ] Docs updated

