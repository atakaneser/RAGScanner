# RS-056: Multi-platform source connector roadmap and contract fixtures

**Objective:** OpenAI vector stores, Qdrant, Chroma, Weaviate, Pinecone, Milvus ve pgvector için öncelik ve contract fixture matrisi hazırlamak.  
**Rationale:** “Çoğu platform desteği” doğrulanabilir capability seviyeleriyle sunulmalıdır.  
**Dependencies:** RS-004/006, ADR-0011; OD-028.  
**Scope:** Source capability matrix, stable identity, documents/chunks/metadata/deletions, auth reference, pagination ve version tiers.  
**Out of scope:** Tüm connector’ları tek issue’da implement etmek.  
**Implementation guidance:** Generic vector-store contract sonrası her platform için ayrı issue; kullanıcı değeri ve API stabilitesine göre sırala.  
**Security considerations:** Tenant/filter semantics, secret refs, SSRF, raw-content consent ve least privilege.  
**Acceptance criteria:** Her platformun rolü, tier’i, gerekli API’leri, riskleri ve ayrı implementation issue’su tanımlı.  
**Tests:** Fixture schema validation ve connector contract test harness.  
**Documentation changes:** Compatibility matrix and connector guide.  
**Completion checklist:** [ ] Matrix [ ] Tiers [ ] Separate issues [ ] Security review [ ] Docs updated

