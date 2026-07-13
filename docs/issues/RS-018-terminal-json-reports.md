# RS-018: Terminal and JSON reports

**Objective:** Produce actionable terminal output and a versioned machine-readable JSON report.  
**Rationale:** These are the first Community result contracts and automation surface.  
**Dependencies:** RS-004, RS-005, scanners, RS-017.  
**Scope:** Summary/category/coverage, finding locations/evidence/remediation, scan provenance/privacy/failures, schema/version, deterministic ordering and exit integration.  
**Out of scope:** HTML, dashboard, PDF, signed reports.  
**Implementation guidance:** Terminal adapts to TTY/color/no-color; JSON stdout contains only JSON; bounded/redacted evidence; publish schema examples.  
**Security considerations:** No ANSI injection, raw control characters, keys, full documents, or unsafe paths; serialization validates untrusted values.  
**Acceptance criteria:** Required report fields present; partial scans unmistakable; JSON validates and is stable; terminal remains readable/accessibility-conscious.  
**Tests:** Golden/snapshot, schema validation, escaping/control chars, large finding pagination/truncation, no-color, leakage.  
**Documentation changes:** Reporting, quickstart, CLI reference.  
**Completion checklist:** [ ] Schema versioned [ ] Golden files [ ] Escape tests [ ] Partial coverage visible [ ] Docs updated

