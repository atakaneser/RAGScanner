# RS-048: Active prompt-injection scan

**Objective:** Test authorized targets for prompt injection, jailbreak, role manipulation, and system-prompt extraction behavior.
**Rationale:** Static document scanning cannot validate a running application's instruction hierarchy.
**Dependencies:** RS-046/047/052/053.
**Scope:** Non-destructive execution, per-test status, refusal/probable/confirmed semantics, and provenance.
**Out of scope:** Tool side effects, source scanning, and automatic exploitation.
**Implementation guidance:** Compare controlled baseline and attack results; never confirm from one payload alone.
**Security:** Explicit authorization, budget/rate limits, response redaction, and no system-prompt retention by default.
**Acceptance:** Vulnerable, safe, refusal, and ambiguous fixtures classify correctly; transport errors are not vulnerabilities.
**Tests:** True/false positive boundaries, timeout, retry, multilingual, and refusal regression.
**Documentation:** Active scan usage and limitations.
**Checklist:** [ ] Authorization gate [ ] Baseline [ ] TP/FP [ ] Provenance [ ] Docs updated
