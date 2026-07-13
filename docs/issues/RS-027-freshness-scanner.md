# RS-027: Basic freshness scanner

**Objective:** Detect explainable stale/version/review/source-index risks from available metadata and comparisons.  
**Rationale:** Aging and mismatched knowledge are central to health and RAG Rot.  
**Dependencies:** RS-004/006/010/016; OD-006/024.  
**Scope:** Configurable age/review thresholds, multiple active versions, missing owner/review date, source digest/index mismatch where observable, broken URL only with explicit network policy.  
**Out of scope:** Assuming filesystem mtime equals content validity, silent URL fetching, full proprietary RAG Rot analytics.  
**Implementation guidance:** Record signal provenance and capability; separate “unknown” from stale; source-specific policy and clocks.  
**Security considerations:** SSRF for URL checks, metadata leakage, clock manipulation, tenant/source boundary, bounded network.  
**Acceptance criteria:** Findings name evidence/threshold; unavailable signals not scored as healthy; time-zone/clock deterministic; network off by default.  
**Tests:** Stale/fresh/unknown, versions, missing dates, clock boundaries, digest mismatch, SSRF/no-network, false positives.  
**Documentation changes:** RAG Rot, scoring, rules/configuration.  
**Completion checklist:** [ ] Unknown semantics [ ] Clock injected [ ] Network policy [ ] TP/FP fixtures [ ] Docs updated

