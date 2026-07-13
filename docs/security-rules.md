# Security rules

RAGScanner includes a versioned active payload/test-case library and an initial deterministic static
rule pack. The static JSON format, matcher boundaries, false-positive/context behavior, and
contribution rules are documented in
[`static-security-scanner.md`](static-security-scanner.md). Active JSON format, safe-mode policy,
controls, placeholder allowlist, and contribution rules are documented in
[`active-security-test-library.md`](active-security-test-library.md).

The active library is separate from the static document rule engine. It describes tests as data and
does not execute a payload by itself. The static scanner also never executes detected or decoded
content.

The initial static pack covers prompt injection, system-prompt extraction, tool/command
instructions, bounded encoded content, invisible/hidden content, metadata poisoning, suspicious
URLs, secrets, and optional PII indicators. Tenant-retrieval and semantic risks are outside this
pack.

Each rule has a stable ID/version, category, description, supported sources, detection phase,
severity, confidence method, evidence-redaction policy, remediation, references, tests, and known
false positives. Severity expresses impact; confidence expresses evidence strength and is displayed
separately. Rules do not fetch arbitrary URLs or trust model classifications.
