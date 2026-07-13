# RS-051: Active context-manipulation scan

**Objective:** Test retrieved-context bypass, poisoning acceptance, and source/citation manipulation.
**Rationale:** Ignoring context or preferring a fake source cannot be proven by static scanning.
**Dependencies:** RS-046/047/052 and retrieval-aware target capability.
**Scope:** Synthetic trusted/untrusted context pairs, override behavior, citation integrity, and abstention.
**Out of scope:** Production-index poisoning and real document mutation.
**Implementation guidance:** Use an ephemeral synthetic collection or target-provided safe fixture.
**Security:** Writing payloads to a production knowledge base is prohibited by default.
**Acceptance:** Context-bypass signals over safe fixtures are explainable and reproducible.
**Tests:** Trusted versus poisoned, refusal, conflicting context, citation mismatch, and cleanup.
**Documentation:** Context-test topology and limitations.
**Checklist:** [ ] Ephemeral fixture [ ] No production mutation [ ] TP/FP [ ] Cleanup [ ] Docs updated
