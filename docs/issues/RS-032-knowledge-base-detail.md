# RS-032: Knowledge-base detail

**Objective:** Present score history, findings, affected sources/evidence/remediation, and scan configuration for one KB.  
**Rationale:** Findings must lead from aggregate score to actionable location.  
**Dependencies:** RS-030/031, RS-033/037 data.  
**Scope:** Current/category scores, history, severity distribution, filters/pagination, documents/source/page/chunk, bounded evidence, recommendation, status/suppression, configuration summary.  
**Out of scope:** Editing raw source content, arbitrary report HTML, advanced comparison.  
**Implementation guidance:** Query by organization+KB; preserve URL filters; disclose score/rule versions and limitations.  
**Security considerations:** Escape evidence/URLs/model text; field-level secret/PII redaction; tenant/authz checks; safe exports.  
**Acceptance criteria:** Every finding can identify available affected location; missing location explicit; filters stable; no unsafe content rendering.  
**Tests:** Component/E2E, XSS corpus, pagination/filter, authz/object IDs, redaction, accessibility.  
**Documentation changes:** Dashboard/findings guide.  
**Completion checklist:** [ ] XSS pass [ ] Tenant isolation [ ] Location UX [ ] A11y pass [ ] Docs updated

