# RS-004: Core models and contracts

**Objective:** Implement versioned domain contracts for scans, sources, documents, chunks, findings, rules, scores, providers, and reports.  
**Rationale:** Stable neutral models prevent adapters and UIs from defining core behavior.  
**Dependencies:** RS-003; OD-024.  
**Scope:** Pydantic/domain value types, enums, invariants, serialization versions, finding fingerprint contract, scan lifecycle and error/coverage model.  
**Out of scope:** Database ORM entities, detector algorithms, API endpoints.  
**Implementation guidance:** Separate domain from wire schemas where change rates differ; use UTC instants and explicit optionality; keep severity/confidence independent.  
**Security considerations:** Bound evidence, validate URLs/identifiers, avoid secret-bearing repr, reject unknown unsafe structures where appropriate.  
**Acceptance criteria:** All specified finding/report fields represented; invalid states fail clearly; schemas round-trip; backward-compatibility policy documented.  
**Tests:** Unit/property tests, serialization golden files, boundary/invalid inputs, fingerprint stability/version tests.  
**Documentation changes:** Architecture data/finding model and generated schema guide.  
**Completion checklist:** [ ] Invariants reviewed [ ] Golden tests [ ] Fingerprint versioned [ ] Security review [ ] Docs updated

