# RS-014: Basic prompt-injection rule engine

**Objective:** Detect deterministic suspicious instructions and obfuscation in documents with explainable confidence.  
**Rationale:** Indirect prompt injection is a core security use case that needs safe, updateable rules.  
**Dependencies:** RS-004, RS-007–010; ADR-0009/OD-022.  
**Scope:** Rule schema/IDs/versions, override/system/tool/shell patterns, Base64/encoded/invisible/hidden/comment signals, bounded decode inspection, suppression-friendly evidence.  
**Out of scope:** Executing payloads, automatic blocking, or claiming complete detection. All maintained rules remain free.  
**Implementation guidance:** Separate candidate signal/confidence from severity; combine signals transparently; use constrained decoding depths/sizes.  
**Security considerations:** Regex/decoder DoS, malicious markup, false positives in security docs/code, evidence leakage, rule-pack integrity.  
**Acceptance criteria:** Synthetic attacks detected at approved thresholds; benign instruction/code fixtures control false positives; rules never execute/fetch content.  
**Tests:** TP/FP, encoded/nested/Unicode/invisible/HTML comment, huge payload/regex timeout, golden rule-version tests.  
**Documentation changes:** Security rules, limitations, remediation, threat model.  
**Completion checklist:** [x] Threat review [x] FP corpus [x] Bounds enforced [x] Severity/confidence separate [x] Docs updated
