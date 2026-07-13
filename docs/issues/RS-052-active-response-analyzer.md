# RS-052: Deterministic active response analyzer

**Objective:** Classify target responses explainably without broad keyword matching.
**Rationale:** Words such as “system” or “API”, and response length alone, create severe false positives.
**Dependencies:** RS-004/047; OD-029.
**Scope:** Baseline delta, exact canary, structured tool events, refusal, combined indicators, confidence, and coverage.
**Out of scope:** Mandatory LLM judges and single-regex confirmed findings.
**Implementation guidance:** Deterministic first; keep confirmed/probable/ambiguous/not-detected separate; report analyzer version.
**Security:** Responses are untrusted and must be escaped, redacted, truncated, and resource-bounded.
**Acceptance:** Labeled-fixture metrics meet the approved threshold; timeout/error is not a vulnerability.
**Tests:** TP/FP, refusal, ambiguity, multilingual, XSS, secrets, and oversized/streaming responses.
**Documentation:** Classification and confidence methodology.
**Checklist:** [ ] Labeled corpus [ ] Baseline delta [ ] Redaction [ ] Metrics [ ] Docs updated
