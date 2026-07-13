# RS-050: Active tool and function abuse scan

**Objective:** Assess tool enumeration, unauthorized invocation, and privilege-escalation risk without side effects.
**Rationale:** Tool abuse is a high-impact risk in agentic RAG systems.
**Dependencies:** RS-046/047/052; OD-026.
**Scope:** Capability-aware dry-run/no-op payloads, tool exposure, authorization refusal, and synthetic canary tools.
**Out of scope:** Sending email, deleting files, running shell commands, or real mutation.
**Implementation guidance:** Require TargetAdapter side-effect metadata and an explicit safe test hook.
**Security:** The default profile cannot mutate; destructive testing is outside this issue.
**Acceptance:** Safe and unsafe fake targets differ without producing a real side effect.
**Tests:** Refusal, enumeration, fake no-op call, permission error, and malformed tool response.
**Documentation:** Tool-testing safety policy.
**Checklist:** [ ] No-op design [ ] No mutation [ ] Contract tests [ ] Audit metadata [ ] Docs updated
