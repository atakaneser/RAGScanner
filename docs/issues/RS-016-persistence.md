# RS-016: Community persistence

**Objective:** Persist scan execution state/artifacts safely in local SQLite behind repository ports.  
**Rationale:** Repeatability, caching/recovery, history, and stable reports need persistence without coupling Core to SQLite.  
**Dependencies:** RS-004; OD-003/007.  
**Scope:** Schema/migrations, transaction boundaries, scan/findings/artifact metadata, retention/cleanup, corruption/recovery, repository adapters.  
**Out of scope:** Remote cloud sync and mandatory multi-user infrastructure.  
**Implementation guidance:** Decide Community history semantics explicitly; use migrations from first release; keep blobs/content minimized and file permissions restrictive.  
**Security considerations:** No plaintext credentials; avoid raw content where possible; safe paths/permissions, parameterized queries, backup deletion semantics.  
**Acceptance criteria:** Fresh/migrated databases work; interrupted writes remain consistent; retention and schema version visible; core has no SQLite dependency.  
**Tests:** Repository contract, migration/rollback, concurrency/locking, corruption/error, permissions, content/secret absence.  
**Documentation changes:** Configuration, privacy, schema/migration guide.  
**Completion checklist:** [ ] Boundary approved [ ] Migrations tested [ ] Retention documented [ ] Security review [ ] Recovery tested
