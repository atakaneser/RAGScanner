# RS-058: Active Security Scan runner

**Objective:** Orchestrate safe test packs, TargetAdapter, and response evaluation in an idempotent active-scan lifecycle.
**Rationale:** An adapter alone is not a scan; authorization, progress, budget, cancellation, and coverage belong in one runner.
**Dependencies:** RS-046/047/057/053/052; ADR-0012/0013.
**Scope:** Authorization acknowledgement, safe default, selection, baseline/attack sequence, progress, budgets, cancellation, per-test results, and occurrences.
**Out of scope:** Destructive payloads, dashboard, scheduler, and static document analysis.
**Implementation guidance:** Pure orchestration with fake target/evaluator; unsupported capabilities become skipped/not-assessed.
**Security:** Disabling safe mode never auto-enables destructive tests; tools use canary/no-op; credentials remain references.
**Acceptance:** Unauthorized scans cannot start; budgets/cancellation are strict; result states remain distinct.
**Tests:** Authorization, safe profile, canary tool, cancel, budget, timeout, partial failure, idempotency, and no-destructive regression.
**Documentation:** Active lifecycle, CLI UX, and authorization warning.
**Checklist:** [ ] Safe default [ ] Authorization gate [ ] Budget/cancel [ ] Result states [ ] Docs updated
