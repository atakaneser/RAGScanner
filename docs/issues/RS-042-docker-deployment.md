# RS-042: Docker deployment

**Objective:** Produce hardened reproducible public container deployment assets.  
**Rationale:** Containers support distribution but enlarge supply-chain/runtime responsibility.  
**Dependencies:** RS-003 and service artifacts; RS-043 for release.  
**Scope:** Multi-stage pinned builds, non-root runtime, minimal images, health/readiness, volumes/config/secrets, compose/dev topology, architecture matrix, SBOM/scan.  
**Out of scope:** Kubernetes platform product, embedding models baked by default, secrets in images.  
**Implementation guidance:** Immutable digest bases, read-only root where feasible, explicit writable paths/resource limits, graceful stop and migrations as separate action.  
**Security considerations:** Capabilities/user, base CVEs, build provenance, registry signing, parser isolation, network/egress and secret mounts.  
**Acceptance criteria:** Reproducible supported-arch image runs non-root; no secrets/dev tools unintended; health/stop/storage work; critical scan findings triaged.  
**Tests:** Image build/smoke, user/filesystem, health/graceful stop, persistence, container scan/SBOM, offline behavior.  
**Documentation changes:** Deployment/install/security/upgrade.  
**Completion checklist:** [ ] Digests pinned [ ] Non-root [ ] SBOM/scan [ ] Resource limits [ ] Docs updated
