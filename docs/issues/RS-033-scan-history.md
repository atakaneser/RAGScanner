# RS-033: Scan history

**Objective:** Provide accurate paginated scan history and scan detail provenance.  
**Rationale:** Continuous monitoring needs auditability and diagnosis of partial/failed scans.  
**Dependencies:** RS-030/029 and self-hosted persistence/jobs.  
**Scope:** Times/duration/source/status, files/chunks/models/privacy/findings/score, failed/skipped checks, artifacts, cancellation/retry visibility.  
**Out of scope:** Comparison logic, schedules, raw document downloads by default.  
**Implementation guidance:** Immutable scan configuration/provenance snapshot; server pagination/filtering; status state machine.  
**Security considerations:** Organization scoping, artifact authorization/expiry, no keys/raw contents, safe provider/filename display.  
**Acceptance criteria:** All specified fields shown; running/partial/failed states unambiguous; timestamps/time zones correct; artifacts authorized.  
**Tests:** State transitions, pagination/filter, time zones, authz/artifact links, XSS/redaction, E2E.  
**Documentation changes:** Scan history/reporting/troubleshooting.  
**Completion checklist:** [ ] Provenance complete [ ] Partial states [ ] Artifact auth [ ] Time tests [ ] Docs updated
