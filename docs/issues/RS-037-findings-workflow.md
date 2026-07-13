# RS-037: Findings workflow and audit history

**Objective:** Support open, acknowledged, resolved, suppressed, and false-positive states with actor/time/reason history.  
**Rationale:** Findings require accountable remediation and recurrence behavior.  
**Dependencies:** RS-005 identity, RS-030/032.  
**Scope:** Transition policy, required reasons, append-only history, suppression scope/expiry, recurrence/reopen behavior, bulk actions with limits.  
**Out of scope:** Source edits, arbitrary rule disablement, future granular RBAC.  
**Implementation guidance:** Domain state machine with optimistic concurrency; separate finding lifecycle from occurrences; preserve audit events.  
**Security considerations:** Tenant authz, actor attribution, tamper-evident audit expectations, stored reason escaping/PII guidance, bulk abuse.  
**Acceptance criteria:** Valid transitions audited; invalid/conflicting updates fail; new occurrence follows documented resolved/suppressed semantics; history immutable to normal users.  
**Tests:** State/property, concurrency, recurrence, suppression expiry/scope, authz, XSS/reason limits, E2E.  
**Documentation changes:** Workflow guide and audit semantics.  
**Completion checklist:** [ ] State diagram approved [ ] Concurrency tests [ ] Audit immutable [ ] Tenant tests [ ] Docs updated

