# RS-055: Active scan controls and safe reports

**Objective:** Add terminal/JSON/HTML reporting, progress, delay/rate limits, budget, and cancellation for active scans.
**Rationale:** Endpoint tests require operational controls and safe evidence.
**Dependencies:** RS-048–054, RS-018/019.
**Scope:** Per-test status, request count/duration, target/analyzer/payload versions, skipped/failed tests, redacted evidence, and exit policy.
**Out of scope:** Fake demo vulnerabilities, raw response dumps, and dashboard.
**Implementation guidance:** Label safe synthetic demos as fixtures; reuse the shared finding/report contract.
**Security:** HTML escaping, secret/PII redaction, response retention limits, and terminal-control handling.
**Acceptance:** Coverage and failed checks are visible; fixtures are not presented as real targets; cancellation is consistent.
**Tests:** Golden JSON, XSS, redaction, budget, cancel, partial failure, and deterministic ordering.
**Documentation:** Active report schema and CLI guide.
**Checklist:** [ ] Coverage [ ] Redaction [ ] No fake result [ ] Exit codes [ ] Docs updated
