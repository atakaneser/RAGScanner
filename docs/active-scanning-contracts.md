# Active scanning contract models

These models are not transports or scanners and perform no network call. The current vendor-neutral
port is documented in [target-adapter-contract.md](target-adapter-contract.md); orchestration is in
[active-scan-runner.md](active-scan-runner.md).

`TargetDefinition` supports bounded target kinds and opaque `env:`, `keychain:`,
`secret-manager:`, `vault:`, or `file-secret:` references. Raw credentials are rejected from
templates, mappings, headers, metadata, requests, responses, executions, evaluations, findings, and
scan metadata.

Active scans require a valid timezone-aware `AuthorizationScope`. Safety defaults to `safe`; a
destructive mode is never implicit. Test cases hold severity, detection class, payload variants,
safe/unsafe/ambiguous indicators, controls, tool access, and side-effect risk. Multilingual payloads
use the same contract.

Target requests must contain no secret values. Responses must be redacted/truncated before model
construction. Execution states are pending, running, completed, failed, skipped, or cancelled.
Evaluation classifications are confirmed, probable, ambiguous, not-detected, and inconclusive;
evaluator types are deterministic, heuristic, LLM-assisted, and manual.

Helpers normalize control characters, redact headers, mask secrets, and truncate values without
mutating caller objects.
