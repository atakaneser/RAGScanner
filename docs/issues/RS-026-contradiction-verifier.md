# RS-026: Optional contradiction verifier

**Objective:** Verify high-value candidate pairs with an explicitly configured model and structured evidence.  
**Rationale:** Some conflicts need contextual judgment after local narrowing.  
**Dependencies:** RS-022–025; OD-004.  
**Scope:** Minimal excerpt prompt/schema, confirmed/not/ambiguous result, citations to both inputs, remediation suggestions, provenance/budget/privacy.  
**Out of scope:** Sending full corpora, autonomous edits, or claiming model judgment is ground truth.  
**Implementation guidance:** Deterministic candidate eligibility; strict schema; conservative ambiguous state; cache keyed by redacted inputs/model/prompt version.  
**Security considerations:** Redact, prevent cross-tenant pairing, treat source/model injection as data, validate citations, bound tokens/cost/retries.  
**Acceptance criteria:** Only opted-in candidates transmit; report exact provider/model/remote use; malformed outputs fail safely; ambiguity does not become confirmation.  
**Tests:** Fake-provider TP/FP/ambiguous, injected source text, bad schema/citations, redaction, budget/cancel, no-network default.  
**Documentation changes:** BYOM, security/privacy, reporting, and free-feature catalog.  
**Completion checklist:** [ ] Boundary decided [ ] Consent proof [ ] Structured validation [ ] Injection tests [ ] Docs updated
