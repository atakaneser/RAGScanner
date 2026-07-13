# RS-028: OpenWebUI connector

**Objective:** Discover/synchronize OpenWebUI knowledge bases and run manual scans through neutral source contracts.  
**Rationale:** OpenWebUI is the first major integration but cannot own scanner logic.  
**Dependencies:** M1/M2 core, RS-029 auth contract; OD-012/021/024.  
**Scope:** Version/capability discovery, KB listing, source/chunk sync, deletions, pagination/rate limits, scoped credentials, manual scan, compatibility fixtures.  
**Out of scope:** Core rules in plugin, guaranteed change triggers, and all OpenWebUI versions.  
**Implementation guidance:** Run API spike first; adapter maps external IDs; checkpoint/idempotent sync; clearly distinguish endpoint locality/data path.  
**Security considerations:** Least privilege, encrypted/reference credential, SSRF/TLS, tenant mapping, content/log minimization, compromised server responses.  
**Acceptance criteria:** Supported versions listed; manual end-to-end scan works; partial/deleted/retried sync correct; connector failure cannot cross KB/tenant.  
**Tests:** Recorded/stub contracts, auth/error/pagination/rate limit, deletion/retry, hostile metadata, credential leakage, optional live matrix.  
**Documentation changes:** Integration guide, compatibility, privacy/troubleshooting.  
**Completion checklist:** [ ] Spike accepted [ ] Version matrix [ ] Sync recovery [ ] Security review [ ] Docs updated
