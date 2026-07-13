# RS-060: Static document Security Scan orchestration

**Objective:** SourceConnector’dan gelen document/chunk/metadata üzerinde sürümlü deterministic/heuristic güvenlik rule’larını çalıştırmak.  
**Rationale:** Active endpoint scan belge içindeki poisoning, hidden instruction, secret ve PII’yi doğrudan incelemez.  
**Dependencies:** RS-004/059/007–010/014/015; ADR-0012.  
**Scope:** Rule execution pipeline, location/evidence/fingerprint, detection class, skipped/failed checks ve static coverage.  
**Out of scope:** Network target request, LLM zorunluluğu, active result inference, automatic remediation.  
**Implementation guidance:** Original ve normalized view; bounded decoding; deterministic first; source capability’ye göre not-assessed.  
**Security considerations:** Parser/rule resource limit, secret evidence redaction, HTML escape, no URL fetch/payload execution.  
**Acceptance criteria:** Static finding document/page/chunk’a bağlanır; active scan sonucu üretmez; TP/FP/boundary/malformed fixture’lar geçer.  
**Tests:** Prompt injection, hidden/encoded, secret/PII, metadata, benign docs, malformed content, limits ve fingerprint stability.  
**Documentation changes:** Static scan CLI, rules, reporting and limitations.  
**Completion checklist:** [x] Source contract [x] Rule versions [x] TP/FP [x] Coverage [x] Docs updated
