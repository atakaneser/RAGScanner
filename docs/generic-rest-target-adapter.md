# Generic REST Target Adapter

The first concrete `TargetAdapter` transports authorized black-box tests to configured JSON REST
targets without provider assumptions. It neither evaluates vulnerabilities nor orchestrates scans.

Configuration covers base URL/path/method, non-secret headers, secret-header references, bounded
JSON request templates, restricted dotted response mappings, timeout/delay/request limits, TLS,
allowed host/port, redirects, maximum response bytes, and optional health path. Secrets are opaque
references; no production resolver backend is included yet.

Allowed request placeholders are `PAYLOAD`, `SESSION_ID`, `CANARY_TOKEN`, `TEST_CASE_ID`, and
`PAYLOAD_ID`. Rendering is literal replacement only—no Jinja, Python, shell, environment expansion,
expression, or recursion. Response text is required; citation, source, tool/function, model, finish
reason, and session fields are optional bounded mappings.

Only HTTP/HTTPS are accepted. URL credentials/fragments are rejected; host/port require an allowlist;
loopback, link-local, multicast, unspecified, and metadata addresses are blocked. Private addresses
require both allowlisting and explicit self-hosted opt-in. All DNS answers are validated immediately
before transport. Redirects default off and every destination is revalidated; cross-host credential
redirects are blocked. Streaming stops at the byte limit. No automatic retry occurs.

The DNS validation/transport-resolution gap leaves a theoretical rebinding window. Validated-IP
pinning remains future hardening. A missing health path performs validation without a request. Active
invocation requires current authorization and safe-mode policy; the adapter never classifies risk.
