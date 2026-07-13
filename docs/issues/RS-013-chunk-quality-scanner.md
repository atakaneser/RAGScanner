# RS-013: Chunk-quality scanner

**Objective:** Detect empty, undersized/oversized, mid-sentence, split structure, multi-topic, overlap, and missing-metadata chunk risks.  
**Rationale:** Bad chunking directly affects retrieval and must point to affected chunks.  
**Dependencies:** RS-004, RS-007–010.  
**Scope:** Deterministic metrics/rules, configurable tokenizer/profile, structure-aware evidence, stable findings.  
**Out of scope:** Universal ideal chunk size, automatic rechunking, model-only topic judgments.  
**Implementation guidance:** Parameterize by language/source/parser; report observed versus threshold; degrade to “not assessed” if structure absent.  
**Security considerations:** Bound tokenization/regex work; escape snippets; avoid storing full chunks.  
**Acceptance criteria:** Each supported signal has TP/FP fixtures and remediation; thresholds/version visible; unsupported inference not asserted.  
**Tests:** Empty/small/large, broken list/table, sentence boundaries, overlap, multilingual, boilerplate, limits and false positives.  
**Documentation changes:** Rule catalog, configuration, report examples.  
**Completion checklist:** [x] Scanner versioned [x] TP/FP coverage [x] Language caveats [x] Bounded limits [x] Docs updated
