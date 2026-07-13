# RS-030: Dashboard authentication and organization foundation

**Objective:** Implement optional secure account/session flows for free multi-user self-hosted deployments.  
**Rationale:** Every dashboard capability depends on trusted identity and tenant context.  
**Dependencies:** RS-029; OD-009/010/023.  
**Scope:** Email/password or passwordless decision, verification/reset as applicable, secure sessions, logout/revocation, account deletion workflow, User/Organization/Membership foundation.  
**Out of scope:** Teams UI, RBAC/SSO, and scanner logic. Single-user local mode must not require authentication.  
**Implementation guidance:** Use proven auth library/provider; create personal organization explicitly; server-side session and authorization middleware; audit sensitive events.  
**Security considerations:** Enumeration, CSRF, XSS/session fixation, cookie policy, rate limiting, token hashing/expiry, MFA future path, deletion/retention.  
**Acceptance criteria:** Complete auth lifecycle; session revoke; verified tenant context; deletion behavior documented; no cross-org access.  
**Tests:** Auth integration/E2E, CSRF/session, enumeration/rate limits, reset expiry/reuse, tenant isolation, deletion.  
**Documentation changes:** Account/security/privacy/support runbooks.  
**Completion checklist:** [ ] Auth ADR [ ] Security review [ ] E2E flows [ ] Tenant tests [ ] Docs updated
