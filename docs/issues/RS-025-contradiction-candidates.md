# RS-025: Local contradiction candidate generation

**Objective:** Narrow potentially conflicting passages deterministically/locally before optional verification.  
**Rationale:** Comparing all chunks with an LLM is costly, private-data heavy, and noisy.  
**Dependencies:** RS-012/020/021, metadata/freshness signals.  
**Scope:** Topic/entity/version/time candidate blocking, negation/numeric/policy heuristics, ranking, candidate evidence and coverage metrics.  
**Out of scope:** Declaring a confirmed contradiction, remote model call, automatic source authority choice.  
**Implementation guidance:** Prefer same subject/scope with changed modality/value/date; distinguish supersession from conflict; cap candidates per group.  
**Security considerations:** Bound pair explosion; minimize evidence; preserve access/tenant boundaries; crafted-text performance tests.  
**Acceptance criteria:** Synthetic contradiction pairs rank above unrelated/superseded cases at approved recall/precision; only candidates are labeled.  
**Tests:** Contradictory/compatible/superseded/ambiguous, multilingual limits, numeric/date, scale/pair caps, deterministic ranking.  
**Documentation changes:** Rule behavior, model privacy example, limitations.  
**Completion checklist:** [ ] Evaluation corpus [ ] Candidate label clear [ ] Pair caps [ ] Tenant boundary [ ] Docs updated

