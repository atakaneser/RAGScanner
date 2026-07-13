# RS-063: Heterogeneous RAG source and environment inventory

**Objective:** Discover and classify RAG knowledge across platform KBs, standalone attachments,
enterprise document systems, bounded websites, SaaS spaces, repositories, object stores, vector
collections, and neutral exports without assuming that a RAG source is a local file.

**Rationale:** A RAG application may reference SharePoint, a website, a vector collection, or an
external retrieval service while exposing little or no raw-file inventory. Scanner coverage must
reflect the capabilities actually available.

**Dependencies:** RS-059, RS-028/056, ADR-0011/0016/0018; OD-010/024/028/031/032/033.

**Scope:** Source-family descriptors, capability tiers, metadata-only inventory, stable external
identity, content/chunk availability, deletion/change signals, retrieval evidence, locality and data-
path disclosure, consent stages, generic manifest/REST import, and separate implementation issues.

**Out of scope:** Silently crawling remote systems, bypassing tenant permissions, claiming universal
connector compatibility, implementing every vendor in one issue, or treating an LLM endpoint as
proof of RAG.

**Security:** Explicit enumeration/content consent, least-privilege credential references, OAuth and
tenant boundaries, SSRF/DNS/redirect defenses, bounded crawling and pagination, hostile metadata
sanitization, secret-safe logs, and no remote model transmission by default.

**Acceptance:** The matrix distinguishes document, chunk, metadata, retrieval-trace, and target-only
capabilities; SharePoint/web/SaaS/Git/object/vector/platform examples map to neutral contracts;
unsupported checks become `not_assessed`; each Tier 1 connector has its own tested issue.

**Tests:** Capability fixtures, pagination/delta/tombstone identity, consent denial, remote boundary,
hostile metadata, credential leakage, duplicate cross-source identity, and partial-coverage reports.

**Documentation:** Connector matrix, source-selection guide, privacy/data-path guide, status, and
roadmap.

**Checklist:** [ ] Matrix [ ] Consent stages [ ] Identity [ ] Generic import [ ] Tier issues
[ ] Security review [ ] Docs updated
