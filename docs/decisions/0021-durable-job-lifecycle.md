# ADR-0021: Durable job lifecycle and cooperative cancellation

- Status: Accepted
- Date: 2026-07-14

## Decision

Represent background work with framework-independent `JobRequest`, `JobRecord`, and `JobRepository`
contracts. Persist the initial queue in SQLite. A worker claims one job with an expiring lease,
renews the lease through explicit checkpoints, and finalizes it through repository-validated state
transitions.

The lifecycle is:

```text
queued -> running -> succeeded
   |         |  \-> queued (bounded retry)
   |         |  \-> failed (attempts exhausted)
   |         \-> cancel_requested -> cancelled
   \-> cancelled
```

Enqueue operations may carry a caller-supplied key that is unique within a job kind. Job payloads
are bounded to 64 KiB and reject embedded credential-like values; secret references such as
`env:NAME` are allowed. Job handlers receive a heartbeat/checkpoint callback and must call it at
safe cooperative-cancellation boundaries.

An expired running lease is reclaimable while attempts remain. An expired lease at the attempt
limit becomes failed. An expired cancellation-requested lease becomes cancelled. Worker exception
details are not persisted because they may contain source data, credentials, or connector output.

## Rationale

This extends ADR-0007 with precise transition and failure semantics while keeping Core independent
of SQLite, FastAPI, and worker processes. Atomic database claims prevent two workers from owning the
same job even though the supported first topology still runs one worker. Explicit checkpoints make
heartbeat and cancellation visible and testable rather than relying on in-process task state.

## Consequences

- The durable queue, production static-scan handler, worker command, and authenticated write API are
  implemented. The scheduler loop remains unavailable.
- Retry effects must be idempotent; future scan persistence must use the job or idempotency key.
- Cancellation is cooperative once work is running. A handler that does not checkpoint can only be
  recovered after its lease expires.
- SQLite remains the initial implementation. The application contracts do not require SQLAlchemy.
