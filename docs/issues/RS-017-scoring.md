# RS-017: Draft RAG Health scoring

**Objective:** Implement a versioned configurable draft scoring policy with category coverage and critical-security caps.  
**Rationale:** Scores must summarize findings without hiding missing assessments or claiming scientific proof.  
**Dependencies:** RS-004, representative scanners; OD-005.  
**Scope:** Policy schema, provisional weights, finding penalties, confidence treatment, caps, coverage/not-assessed, explanations, snapshots.  
**Out of scope:** Validated marketing claims, RAG Rot formula, ML-based scoring.  
**Implementation guidance:** Pure deterministic calculator; preserve inputs/policy version; comparisons warn on policy changes; default weights configurable.  
**Security considerations:** Critical findings cannot be averaged away; prevent malformed policies/NaN/range errors and score gaming through skipped checks.  
**Acceptance criteria:** Score/category/coverage reproduce from stored inputs; cap and missing-data behavior explicit; calibration limitations appear in outputs.  
**Tests:** Golden/property/monotonicity, boundary weights, skipped/failed checks, cap cases, policy-version comparison.  
**Documentation changes:** Scoring, reporting, product limitations.  
**Completion checklist:** [x] Policy approved [x] Coverage visible [x] Golden vectors [x] No scientific claim [x] Docs updated
