# RS-044: Security hardening and verification

**Objective:** Threat-model and verify the complete supported product before release.  
**Rationale:** Parsers, untrusted knowledge, models, connectors, tenancy, jobs, and supply chain form a high-risk surface.  
**Dependencies:** Relevant milestone features; SECURITY requirements.  
**Scope:** Data-flow threat model, parser sandbox/limits, XSS/SSRF/injection, authn/authz/tenant tests, secrets/PII/logging, LLM output, webhook, dependency/container/secret scans, response policy.  
**Out of scope:** Claiming perfect security, replacing independent review, testing unauthorized third parties.  
**Implementation guidance:** Maintain abuse cases and security regression suite; prioritize trust boundaries; seek external review before a production-ready release.  
**Security considerations:** This issue is security-focused; handle findings privately, use synthetic data, coordinate disclosure and severity/remediation.  
**Acceptance criteria:** Threat model reviewed; no unresolved release-blocking findings; limits and tenant matrix pass; security contact/support versions established; residual risks documented.  
**Tests:** Malformed/fuzz, archive bombs, XSS/SSRF, authz/tenant, secret leakage, model injection/schema, webhook/replay, supply-chain scans.  
**Documentation changes:** SECURITY, privacy, architecture, operational runbooks/advisories.  
**Completion checklist:** [ ] Threat model [ ] Regression suite [ ] External review decision [ ] Blockers closed [ ] Residual risks approved
