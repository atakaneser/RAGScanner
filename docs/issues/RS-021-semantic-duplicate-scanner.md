# RS-021: Semantic duplicate scanner

**Objective:** Find semantically duplicative chunks using local embeddings and efficient candidates.  
**Rationale:** Paraphrased redundant content escapes lexical similarity.  
**Dependencies:** RS-012, RS-020.  
**Scope:** Vector candidate/index strategy, threshold/profile, cluster/group explanation, model provenance, stable findings and bounded evidence.  
**Out of scope:** Universal semantic equivalence, contradiction decisions, remote-only requirement.  
**Implementation guidance:** Filter exact/near duplicates first; benchmark ANN versus bounded exact similarity; calibration is model/language specific.  
**Security considerations:** Bound vector count/memory/pairs, untrusted model artifacts, evidence minimization, poisoned embedding considerations.  
**Acceptance criteria:** Approved TP/FP corpus and scale target; deterministic enough under fixed config; reports model/threshold and limitations; skipped visibly without model.  
**Tests:** Paraphrase positives, same-topic false positives, multilingual/short chunks, thresholds, scale/memory, provider failure.  
**Documentation changes:** Models, rule catalog, scoring/limitations.  
**Completion checklist:** [ ] Evaluation recorded [ ] FP target [ ] Scale target [ ] Provenance visible [ ] Docs updated

