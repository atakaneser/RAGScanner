# Testing strategy

## Principles

Every feature ships with tests proportionate to failure impact. Default CI is deterministic, offline, synthetic, and requires no cloud credentials. Tests evaluate both true positives and false positives; a detector that finds attacks but flags normal documentation excessively is not complete.

## Layers

- Unit/property: domain invariants, normalization, fingerprints, score policies, rules, state machines, schedule/time boundaries.
- Parser contracts/fixtures: healthy, empty, malformed, oversized, adversarial and structure-preserving cases for each format.
- Scanner evaluation: versioned labeled TP/FP/boundary corpora, metrics and accepted thresholds by rule/profile/language.
- Adapter contracts: filesystem, persistence, providers, connectors, queues and notifications against deterministic fakes.
- Target adapter contracts: OpenAI-compatible, TGI, OpenWebUI, and custom REST response fixtures; CI uses no real endpoint or API key.
- Active security evaluation: vulnerable/safe/refusal/ambiguous responses, false-positive, and multilingual fixtures for each payload; a model name or long response alone is not a vulnerability.
- Integration: CLI pipeline, repositories/migrations, API/auth, workers/jobs, reports and external-service stubs.
- Security: archive bombs/parser limits, fuzz seeds, XSS, SSRF, injection/encoded payloads, secret leakage, authz/tenant isolation, webhook replay/signature.
- End-to-end: install-to-report smoke; dashboard-to-scan-to-finding; scheduling/notification; upgrade/rollback.
- Non-functional: scale/memory/time budgets, concurrency, cancellation, accessibility, load/soak, backup/restore and disaster drills.

## Required synthetic knowledge fixtures

Healthy; exact/near duplicates; contradictions and superseded non-conflicts; stale/versioned content; prompt injection; encoded/Base64/invisible/HTML-comment payloads; inert synthetic secrets; multilingual; malformed/empty PDF; oversized chunk; broken list/table; repeated headers/footers; and false-positive security/code/policy examples. Fixtures are generated or licensed for redistribution and contain no real personal/customer data.

Active Scan fixtures also cover system-prompt refusal, safe tool refusal, simulated leakage,
function enumeration, context bypass, rate limit, timeout, malformed JSON, streaming, oversized
responses, and redaction. Demo fixtures cannot be reported as real scan results.

## Reproducibility and gates

Pin scanner/rule/model/normalization/tokenizer versions in golden results. Changes to expected findings or scores require an explained review, not blind snapshot updates. CI gates include lint/format/types/unit/integration/security/dependency/secret/docs checks; release gates add packaging/install, schema compatibility, containers/SBOM/provenance, supported matrix, E2E, and milestone-specific security/readiness evidence.

Alpha CI supports Python 3.12 and 3.13, builds wheel/sdist, runs a synthetic report smoke and checks
local Markdown links. Release verification additionally installs the wheel into a clean environment
and confirms bundled rule/schema resources.

## Test data safety

Never copy production documents, keys, reports, email addresses, or endpoints into tests. Synthetic “secrets” must be unmistakably inert. Failure output and snapshots are checked for sensitive-value leakage.
