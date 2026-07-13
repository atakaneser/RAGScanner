# RS-059: Static SourceConnector contract

**Objective:** Define a vendor-neutral source contract for documents, chunks, metadata, and knowledge-base content.
**Rationale:** Filesystem, OpenWebUI, and vector-store adapters must not mix with TargetAdapter or ModelProvider.
**Dependencies:** RS-004; ADR-0011/0012.
**Scope:** Capabilities, source listing, content reads, stable identity, pagination, deletion/tombstone, trace availability, and errors.
**Out of scope:** Filesystem/OpenWebUI implementations, network calls, active tests, and model inference.
**Implementation guidance:** Protocol/ABC plus deterministic fake; raw-content availability is a separate capability.
**Security:** Secret references, tenant/filter provenance, content minimization, and access-scope metadata.
**Acceptance:** Fake contract passes; no TargetAdapter/ModelProvider imports; unavailable capability becomes not-assessed.
**Tests:** Pagination, identity, deletion, partial error, unavailable content, and serialization fixtures.
**Documentation:** Source connector SDK and capability guide.
**Checklist:** [x] Contract [x] Fake source [x] Identity model [x] No network [x] Docs updated
