# RS-059: Static SourceConnector contract

**Objective:** Document, chunk, metadata ve knowledge-base content okumak için vendor-neutral static source sözleşmesini oluşturmak.  
**Rationale:** Filesystem, OpenWebUI ve vector-store adapter’ları TargetAdapter veya ModelProvider ile karışmamalıdır.  
**Dependencies:** RS-004; ADR-0011/0012.  
**Scope:** Capability, list sources, fetch documents/chunks, stable source identity, pagination, deletion/tombstone, retrieval trace availability ve error contract.  
**Out of scope:** Filesystem/OpenWebUI implementation, network, active test ve model inference.  
**Implementation guidance:** Protocol/ABC ve deterministic fake; raw content availability ayrı capability.  
**Security considerations:** Secret reference, tenant/filter provenance, content minimization ve source access scope metadata.  
**Acceptance criteria:** Fake connector contract geçer; TargetAdapter/ModelProvider import yok; unavailable capability not-assessed olur.  
**Tests:** Pagination, stable identity, deletion, partial error, unavailable content ve serialization golden files.  
**Documentation changes:** Source connector SDK and capability guide.  
**Completion checklist:** [ ] Contract [ ] Fake source [ ] Identity model [ ] No network [ ] Docs updated

