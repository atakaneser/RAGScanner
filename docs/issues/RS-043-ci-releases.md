# RS-043: CI and releases

**Objective:** Establish protected, reproducible, signed, semantically versioned test and release pipelines.  
**Rationale:** Public delivery needs confidence, provenance, and compatibility.  
**Dependencies:** RS-003; release artifacts as added; licensing decision.  
**Scope:** PR checks, Python/web matrices, secret/dependency/container scans, docs/links, build artifacts, changelog/release notes, tags, provenance/signing, protected environments.  
**Out of scope:** Publishing before explicit approval, force-pushing main, real model credentials in CI.  
**Implementation guidance:** Least-privilege pinned actions, OIDC where possible, deterministic fakes, artifact promotion rather than rebuild, manual protected publish gate.  
**Security considerations:** Workflow injection, untrusted forks, action pinning, token permissions, cache poisoning, signing keys, dependency confusion.  
**Acceptance criteria:** PR checks reliable; release dry run reproducible/verified; no credentials for tests; failure blocks publish; version/changelog/schema compatibility enforced.  
**Tests:** CI fixture PR, release dry run, permission review, tamper verification, failure paths, restore artifacts.  
**Documentation changes:** Contributing, deployment, changelog/release runbook.  
**Completion checklist:** [ ] Actions pinned [ ] Permissions minimal [ ] Dry run [ ] Provenance verifies [ ] Docs updated
