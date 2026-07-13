# RS-049: Active data-leakage scan

**Objective:** Safely test context, cross-session, secret/PII, and knowledge-base disclosure behavior.
**Rationale:** Leakage is reliable only with target responses and authorized synthetic canaries.
**Dependencies:** RS-046/047/052.
**Scope:** Synthetic canaries, context enumeration, prior-session probes, redacted evidence, and confidence.
**Out of scope:** Real customer-data collection, training-data extraction claims, and tenant SaaS.
**Implementation guidance:** Broad keyword matches cannot be confirmed without a known synthetic canary.
**Security:** Minimize response retention and mask real secrets/PII at the report boundary.
**Acceptance:** Canary leakage is detected without false positives on safe refusals or documentation.
**Tests:** Canary TP, refusal FP, PII redaction, cross-session fake, and oversized response.
**Documentation:** Leakage methodology and legal warning.
**Checklist:** [ ] Canary model [ ] Redaction [ ] TP/FP [ ] No real data [ ] Docs updated
