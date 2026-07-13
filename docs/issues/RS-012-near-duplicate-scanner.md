# RS-012: Near-duplicate scanner

**Objective:** Detect explainable lexical near-duplicate documents/chunks offline.  
**Rationale:** Version copies and repeated content degrade retrieval but cannot be found by exact hashing alone.  
**Dependencies:** RS-004, RS-010, RS-011.  
**Scope:** Evaluate MinHash/SimHash/Jaccard, candidate indexing, thresholds by content size/type, similarity evidence and version-candidate signal.  
**Out of scope:** Embedding semantics, definitive active-version resolution, quadratic all-pairs scans.  
**Implementation guidance:** Benchmark algorithms on synthetic corpora; separate candidate generation from decision; expose threshold/profile/version.  
**Security considerations:** Bound tokens/memory/pairs, prevent crafted collision/performance abuse, minimize evidence.  
**Acceptance criteria:** Approved TP/FP thresholds, sub-quadratic candidate path, deterministic results, clear confidence and limitations.  
**Tests:** Near-copy positives, boilerplate false positives, multilingual/short/large boundaries, collision/performance and deterministic tests.  
**Documentation changes:** Algorithm, configuration, limitations, scoring impact.  
**Completion checklist:** [x] Algorithm documented [x] Conservative default threshold [x] FP fixtures [x] Limits pass [x] Docs updated
