# RS-035: Scheduler and worker orchestration

**Objective:** Execute manual/daily/weekly/custom scheduled scans reliably and time-zone correctly.  
**Rationale:** Continuous monitoring is a useful free operational capability after the scanner core is reliable.  
**Dependencies:** RS-029/030/033; ADR-0007; OD-008.  
**Scope:** Schedule CRUD/pause/resume, validated cron-like format, timezone/DST, durable job creation, leases/retries/cancel/idempotency, missed-run policy and next run.  
**Out of scope:** Change triggers, notification delivery, arbitrary user code.  
**Implementation guidance:** Store schedule timezone/expression/version; calculate intended run; at-least-once delivery with idempotent effects; capacity/backpressure.  
**Security considerations:** Org authz, schedule abuse/rate limits, credential resolution only in worker, poisoned jobs, log redaction.  
**Acceptance criteria:** No duplicate scan effect; DST/missed/retry semantics documented/tested; pause prevents future enqueue; stuck jobs recover visibly.  
**Tests:** Unit clock/DST/cron, integration queue/retry/lease, duplicate delivery, pause/resume, tenant authz, failure recovery.  
**Documentation changes:** Scheduling, deployment/runbooks, troubleshooting.  
**Completion checklist:** [ ] Tech decision [ ] DST matrix [ ] Idempotency proof [ ] Recovery drill [ ] Docs updated
