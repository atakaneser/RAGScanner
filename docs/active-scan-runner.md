# Active security scan runner

`ActiveSecurityScanRunner` performs in-memory orchestration between the versioned test library,
provider-neutral `TargetAdapter`, and response evaluator. It contains no persistence, API, UI,
distributed worker, reporting, or automatic retry.

After plan validation it verifies descriptor and authorization, selects tests deterministically by
ID/category/tag/language/capability/safety, optionally runs one control per case, invokes attacks
sequentially, evaluates observations, and emits findings/events. Unsupported tests become structured
skips. Configuration and authorization failures fail closed before transport.

Safe mode is default. Production targets accept only safe mode; destructive tests require explicit
plan and target capability and remain outside normal operation. Runtime placeholders use synthetic
canary/session/no-op/document/user values—never authorization actors, credentials, or personal data.

Request, duration, and failure budgets are checked before and after control/attack calls.
Cancellation reaches the active adapter invocation. A failed control is not a vulnerability and the
attack may be evaluated without it. Concurrency is one for deterministic ordering and burst control.

`confirmed` and `probable` results create findings; `ambiguous` is retained only under explicit
manual-review policy. `not_detected`, transport failures, and `inconclusive` do not create
vulnerability findings. Severity comes from the case, confidence from evaluation, and classification
is never upgraded by the runner.

Known limits: sequential and in-memory only, no restart recovery/distributed cancellation, no score.
