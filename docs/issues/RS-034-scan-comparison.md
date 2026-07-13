# RS-034: Scan comparison

**Objective:** Compare two compatible scans for new/resolved/recurring findings, document changes, severity and score/RAG Rot differences.  
**Rationale:** Deterioration and remediation are visible only across time.  
**Dependencies:** RS-005 identity model, RS-033, RS-017/027.  
**Scope:** Compatibility checks, stable fingerprint matching, change classifications, policy/rule/source-version warnings, paginated UI/API.  
**Out of scope:** Claiming causation, comparing unrelated KBs by default, automatic remediation.  
**Implementation guidance:** Pure comparison service; separate “not observed” from resolved when coverage differs; preserve occurrence evidence.  
**Security considerations:** Both scans same authorized org/KB; bounded evidence; cache keys tenant-scoped.  
**Acceptance criteria:** Required change groups correct; incompatible/coverage-changed scans warn or refuse; algorithm deterministic and explainable.  
**Tests:** Golden comparison scenarios, fingerprint versions, missing checks/documents, severity/status changes, authz, scale.  
**Documentation changes:** Comparison semantics and limitations.  
**Completion checklist:** [x] Resolution semantics [x] Compatibility guard [x] Initial deterministic
tests [ ] Document-change comparison [ ] API pagination/scale [ ] Tenant tests [x] Initial docs
