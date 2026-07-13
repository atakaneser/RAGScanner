# RS-011: Exact duplicate scanner

**Objective:** Detect duplicate documents/chunks using versioned canonical digests.  
**Rationale:** Exact duplicates are high-confidence, explainable first findings.  
**Dependencies:** RS-004, RS-010.  
**Scope:** SHA-256 identities, grouping, canonical representative, document/chunk rules, stable fingerprint/evidence/recommendation.  
**Out of scope:** Near/semantic similarity, automatic deletion.  
**Implementation guidance:** Distinguish byte duplicate from normalized-text duplicate; stream where possible; define empty-content behavior.  
**Security considerations:** Do not expose full duplicate content; avoid digest misuse as authentication; bound group evidence.  
**Acceptance criteria:** Exact groups and affected locations are correct/stable; empty documents handled separately; report explains digest basis.  
**Tests:** True/false positives, normalization variants, empty/large files, hash golden vectors, deterministic grouping/order.  
**Documentation changes:** Rule catalog and reporting examples.  
**Completion checklist:** [x] Rule IDs/version [x] TP/FP fixtures [x] Evidence bounded [x] Bounded limits [x] Docs updated
