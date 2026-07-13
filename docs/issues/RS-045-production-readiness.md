# RS-045: Production readiness review

**Objective:** Prove the selected release is operable, supportable, recoverable, compliant enough, and truthfully marketed.  
**Rationale:** Feature completion alone does not make a reliable public product.  
**Dependencies:** RS-038–044 and milestone exit criteria.  
**Scope:** SLOs/alerts, load/capacity/cost, migrations, backup/restore/DR, retention/deletion, incident/support/on-call, accessibility, legal/privacy, release/rollback, compatibility and launch checklist.  
**Out of scope:** Guaranteeing zero incidents, unresolved future enterprise features.  
**Implementation guidance:** Evidence-based review with owners; run restore, rollback, incident tabletop and critical E2E; document go/no-go.  
**Security considerations:** Close release blockers, key rotation/recovery, access reviews, audit retention, breach handling and dependency posture.  
**Acceptance criteria:** Approved SLOs/runbooks; drills meet targets; capacity/cost known; legal/security/accessibility reviews complete; claims match shipped features; rollback viable.  
**Tests:** Load/soak, disaster restore, migration/rollback, incident tabletop, E2E, accessibility, and security regression.  
**Documentation changes:** Status, support, deployment, privacy/terms, release notes and runbooks.  
**Completion checklist:** [ ] Go/no-go signed [ ] Drills passed [ ] SLO/alerts [ ] Support/legal ready [ ] Status truthful
