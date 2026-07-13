# RS-005: Community CLI

**Objective:** Provide a safe, composable CLI entry point for local scans and diagnostics.  
**Rationale:** The CLI is the first Community user surface and automation contract.  
**Dependencies:** RS-003, RS-004; scan pipeline issues for full command.  
**Scope:** Typer command tree, config resolution, exit codes, progress/quiet/non-interactive behavior, version/help, scan orchestration interface.  
**Out of scope:** Scheduling, hosted login, shell execution, detector implementation.  
**Implementation guidance:** Keep presentation at the edge; make JSON mode stdout machine-clean and diagnostics stderr; define cancellation and partial-failure exits.  
**Security considerations:** Never print keys/content by default; reject unsafe paths/options; avoid command construction; redact error context.  
**Acceptance criteria:** Help/version work offline; deterministic exit codes; invalid configuration is actionable; repeated local scans are not artificially limited.  
**Tests:** CLI runner unit/integration, snapshots, Unicode/path/boundary, interrupt, stdout/stderr and secret-redaction tests.  
**Documentation changes:** Quickstart, configuration, troubleshooting.  
**Completion checklist:** [ ] UX reviewed [ ] Exit codes documented [ ] Redaction tested [ ] Cross-platform paths [ ] Docs updated

