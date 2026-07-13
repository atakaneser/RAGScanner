# ADR-0016: Guided onboarding and consent-based source discovery

- Status: Accepted
- Date: 2026-07-13

## Decision

Running `ragscanner` without arguments opens an English interactive flow that guides a user through
source type, source location, and the first scan. Existing explicit subcommands remain available for
automation and advanced use.

Local discovery is bounded and metadata-only. By default it inspects only the working directory and
known immediate child directories for supported extensions. It never crawls the entire home
directory or disk. Local service discovery runs only after explicit consent and sends short,
redirect-free requests to fixed loopback health endpoints. A health response creates only a
candidate; it does not prove product identity, version compatibility, or authorization.

Before a connector reads document or chunk content, RAGScanner displays the source, endpoint,
credential reference, selected knowledge base, and local/remote data path and requests separate
consent. Discovery never merges the `SourceConnector`, `TargetAdapter`, and `ModelProvider` roles.

All product-generated labels, messages, remediation text, metadata, canonical documentation, and UI
output are English. Source-derived evidence remains in its original language so reports preserve
audit fidelity. Parsers, normalizers, rules, and path handling remain Unicode-native and
multilingual. Explicitly named localized README files are the only non-English documentation
exception.

## Rationale

Requiring users to know CLI syntax and storage locations creates unnecessary onboarding friction.
Unbounded filesystem crawling, silent localhost probing, or automatic remote content retrieval
would violate local-first and least-privilege principles. Guided, staged discovery addresses both
concerns.

## Consequences

- The CLI and future dashboard can share application-level onboarding and discovery services.
- `doctor` remains network-free.
- Non-interactive use remains deterministic through explicit subcommands.
- Planned connectors are never presented as implemented.
- Multilingual input is supported without localizing product-generated output.
