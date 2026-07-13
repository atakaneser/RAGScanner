# RS-031: Dashboard overview

**Objective:** Show organization knowledge bases and current operational health at a glance.  
**Rationale:** Operators need prioritized deterioration/critical-risk context, not vanity charts.  
**Dependencies:** RS-030, knowledge-base/scan/read models, RS-017/027.  
**Scope:** KB list, health/RAG Rot, last scan/status, critical findings, score change, next schedule, empty/error/loading/stale states.  
**Out of scope:** Detail/workflow edits and scanner algorithms.  
**Implementation guidance:** Server-authorized read model; make policy/version/coverage and not-assessed states visible; accessible responsive components.  
**Security considerations:** Organization scoping, no evidence/content on overview, safe error states, cache partitioning.  
**Acceptance criteria:** Required fields and partial/stale states accurate; critical risks prioritized; deep links preserve tenant auth; WCAG target met.  
**Tests:** Unit/component, API authz, E2E empty/populated/error, accessibility, cross-tenant/cache tests.  
**Documentation changes:** Dashboard user guide and screenshots only from synthetic data.  
**Current slice:** A browser-tested single-user localhost overview shows latest posture/coverage,
recent scans, durable jobs, and queue controls. Organization knowledge bases, trends, schedules,
declared WCAG/browser acceptance, and tenant behavior remain open.
**Completion checklist:** [ ] UX review [ ] Coverage visible [ ] A11y pass [ ] Tenant tests [ ] Docs updated
