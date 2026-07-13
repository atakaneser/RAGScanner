# RS-060: Static document Security Scan orchestration

**Objective:** Run versioned deterministic/heuristic security rules over source documents, chunks, and metadata.
**Rationale:** Active endpoint scanning does not directly inspect poisoning, hidden instructions, secrets, or PII in documents.
**Dependencies:** RS-004/059/007–010/014/015; ADR-0012.
**Scope:** Rule pipeline, locations/evidence/fingerprints, detection class, skipped/failed checks, and static coverage.
**Out of scope:** Network target requests, mandatory LLMs, active-result inference, and automatic remediation.
**Implementation guidance:** Preserve original/normalized views; bounded decoding; deterministic first; capability-based not-assessed.
**Security:** Parser/rule resource limits, evidence redaction, HTML escaping, and no URL fetch or payload execution.
**Acceptance:** Findings link to document/page/chunk and never imply active-scan results; TP/FP/boundary/malformed fixtures pass.
**Tests:** Injection, hidden/encoded content, secret/PII, metadata, benign/malformed content, limits, and fingerprint stability.
**Documentation:** Static CLI, rules, reporting, and limitations.
**Checklist:** [x] Source contract [x] Rule versions [x] TP/FP [x] Coverage [x] Docs updated
