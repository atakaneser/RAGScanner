# RS-015: Secret scanner

**Objective:** Detect likely secrets/credentials/connection strings locally with redacted evidence.  
**Rationale:** Indexed credentials are high-impact and must never be amplified by reports.  
**Dependencies:** RS-004, RS-007–010; rule framework alignment with RS-014.  
**Scope:** High-confidence formats plus entropy/context rules, allowlist/suppression hooks, type/location, irreversible redaction/fingerprint.  
**Out of scope:** Credential validity checks, network calls, exhaustive PII scanning, secret rotation.  
**Implementation guidance:** Never retain full match; fingerprint a protected/canonical value without making short secrets guessable; recommend rotation/removal.  
**Security considerations:** Logs/reports/test snapshots must not contain secrets; synthetic tokens must be inert; bound entropy/regex operations.  
**Acceptance criteria:** Known fixture types detected; placeholders/UUIDs/docs examples meet FP targets; output cannot reconstruct the secret; no validation network traffic.  
**Tests:** TP/FP/boundary, redaction, logging/repr/JSON/HTML leakage, Unicode/large files, rule performance.  
**Documentation changes:** Security rules, privacy, remediation and limitations.  
**Completion checklist:** [x] Synthetic fixtures [x] Leakage tests [x] FP review [x] No network [x] Docs updated
