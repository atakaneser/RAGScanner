# TargetAdapter contract

`TargetAdapter` is a vendor-neutral async port that prepares and transports authorized active
black-box tests to a running RAG/LLM application. It is not a source connector, model provider,
vulnerability evaluator, or scan runner.

Retrieval capability defaults false and must be explicitly demonstrated before a target is labeled
RAG. `prepare_invocation` validates authorization, safe mode, capabilities, and budget without
network access. `invoke` transports a prepared request under concrete timeout/rate/budget controls;
evaluation remains separate because identical responses may mean different things by test context.

Session creation, model discovery, and cancellation are optional capabilities. Safety defaults to
safe; destructive mode requires explicit selection and target capability, while production-unsafe
payloads remain blocked. Tool tests use canary/dry-run/no-op behavior.

Budgets cover request count, duration, failures, and rate-limit delay. Credentials are opaque
references. Headers, query values, response bodies, citations, source excerpts, and tool arguments
must be bounded and redacted before serialization. Transport errors are not findings.

`FakeTargetAdapter` is deterministic in-memory test support with no network/filesystem access.
