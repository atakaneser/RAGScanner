# Product definition

## Purpose

RAGScanner is a free, open-source platform for inspecting whether knowledge, retrieval results, and
answers used by Retrieval-Augmented Generation systems are safe, current, reliable, and efficient.
It reports affected sources, documents, pages, chunks, queries, retrieval results, or answers and
offers actionable remediation—not only abstract scores.

Positioning: **“Scan your RAG before your users do.”**

## One product

CLI, Core, API, worker, scheduler, dashboard, connectors, security rules, reports, and documentation
belong to one public repository and remain free. There is no paid edition, subscription,
entitlement, license server, private rule feed, or artificial feature restriction.

## Usage and analysis modes

- One-time local file/folder scans and offline security/health analysis
- Local/self-hosted history, comparison, scheduling, and change-triggered scans (planned)
- OpenWebUI and additional source integration (planned)
- Optional user-controlled models and local embeddings (planned)
- Terminal, JSON, standalone HTML, and dashboard reports

`offline` uses deterministic/heuristic checks and optional local embeddings without a chat-model
call. `balanced` may send only minimum redacted excerpts to an explicitly configured model. `deep`
may add synthetic tests and expensive verification. Remote model use always requires explicit
configuration and consent.

## Security Scan

Security Scan covers prompt injection and instruction override, system-prompt extraction, tool and
command manipulation, hidden/invisible content, HTML comments, encoded payloads, suspicious URLs,
data poisoning, metadata manipulation, credentials, PII, and retrieval access-control risks.

A security finding keeps severity separate from confidence and records detection class, location,
bounded/redacted evidence, impact, remediation, rule/version, and fingerprint. LLM-assisted output
is not a confirmed vulnerability without deterministic or controlled evidence.

- **Static/passive:** inspect document, chunk, and metadata content locally.
- **Active/dynamic:** send versioned safe tests to an explicitly authorized running application.

Active testing defaults to `safe`, enforces timeout/rate/request budgets and cancellation, and never
enables destructive or side-effect-capable tests automatically. Tool tests use canary, dry-run, or
no-op actions. `not_detected` is not a security guarantee.

## Adapter roles

1. `SourceConnector` reads documents, chunks, metadata, or knowledge-base content.
2. `TargetAdapter` sends authorized tests to a running application.
3. `ModelProvider` supplies an optional model for RAGScanner's own analysis.

One platform may fill multiple roles, but each role has separate configuration, credential
references, consent, and provenance. An LLM endpoint is not necessarily a RAG system. Retrieval must
be verified before a target is labeled `rag`. OpenWebUI is one integration, not Core.

## Health Scan and scores

Health analysis includes exact/near/semantic duplicates, malformed content, chunk quality,
metadata, freshness, superseded versions, source-index mismatch, contradiction candidates, and
retrieval/answer signals. A check without required source capability or ground truth is
`not_assessed`, never successful by assumption.

RAG Health Score and RAG Rot are configurable, versioned product metrics rather than scientific
standards. Reports expose coverage, skipped/failed checks, and policy version. Critical security
findings may cap an overall score once the score policy is finalized.

## Local operation and authentication

The first dashboard targets one user on localhost or a private network. It has no public signup,
organization, membership, RBAC, SSO, subscription, or entitlement model. Deployments exposed beyond
localhost must use reverse-proxy authentication, VPN, or another private-network control.

## Explicitly out of initial scope

- Multi-tenant SaaS, public account management, and mandatory Kubernetes/microservices
- Supporting every vector database in the first release
- Automatic source mutation, exploit execution, or payload side effects
- Presenting scores as scientific, correctness, or security guarantees

## Primary risks

- False positives causing fatigue or missed attacks causing false confidence
- Parser, rule-pack, dependency, and model supply-chain attacks
- Data leakage through remote models or misconfigured connectors
- Resource exhaustion during decoding/parsing
- OpenWebUI and other upstream API changes
- Dashboard/scheduler scope delaying Core quality
- Open-source maintenance and coordinated-disclosure capacity
