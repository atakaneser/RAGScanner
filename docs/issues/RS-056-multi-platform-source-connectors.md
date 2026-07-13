# RS-056: Multi-platform source connector roadmap and contract fixtures

**Objective:** Define priority and contract-fixture matrices for OpenAI vector stores, Qdrant, Chroma, Weaviate, Pinecone, Milvus, and pgvector.
**Rationale:** Broad platform support must use verifiable capability tiers.
**Dependencies:** RS-004/006, ADR-0011; OD-028.
**Scope:** Source capability matrix, stable identity, documents/chunks/metadata/deletions, auth references, pagination, and version tiers.
**Out of scope:** Implementing every connector in one issue.
**Implementation guidance:** Create one issue per platform after the generic source contract; prioritize user value and API stability.
**Security:** Tenant/filter semantics, secret references, SSRF, raw-content consent, and least privilege.
**Acceptance:** Each platform has a role, tier, required APIs, risks, and a separate implementation issue.
**Tests:** Fixture-schema validation and connector contract harness.
**Documentation:** Compatibility matrix and connector guide.
**Checklist:** [ ] Matrix [ ] Tiers [ ] Separate issues [ ] Security review [ ] Docs updated
