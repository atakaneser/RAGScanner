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
- Opt-in local SQLite history, coverage-aware comparison, and editable recurring interval schedules;
  calendar rules and change-triggered scans remain planned
- Localhost history/detail/comparison API plus scoped Bearer-authenticated asynchronous scan and job
  control
- Localized saved-report downloads as standalone HTML, structured Excel workbooks, and paginated PDF
- Durable SQLite static-scan jobs with CLI enqueue/control and a user-facing worker process
- Consent-gated OpenWebUI knowledge content scans; heterogeneous enterprise, web, repository,
  object-store, and vector sources remain planned
- Optional user-controlled models and local embeddings (planned)
- Terminal, JSON, standalone HTML, and a local overview/queue dashboard

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

RAG knowledge is not assumed to be a local file. A source may be a SharePoint site/drive/list, web
page or sitemap, SaaS knowledge space, Git tree, object-store prefix, vector collection, platform
knowledge base, chat attachment, or neutral export manifest. Capability discovery determines which
security/quality checks are assessable; unavailable content or provenance becomes `not_assessed`,
never healthy by assumption.

## Health Scan and scores

Health analysis includes exact/near/semantic duplicates, malformed content, chunk quality,
metadata, freshness, superseded versions, source-index mismatch, and retrieval/answer signals.
Contradiction candidates may return only after an implementation meets the product accuracy bar.
A check without required source capability or ground truth is
`not_assessed`, never successful by assumption.

RAG Health Score and RAG Rot are configurable, versioned product metrics rather than scientific
standards. Reports expose coverage, skipped/failed checks, and policy version. Critical security
findings may cap an overall score once the score policy is finalized.

The implemented report score combines assessed security, knowledge-quality, and efficiency
dimensions. Contradiction detection was removed because the bounded labelled-value heuristic did
not meet the product's accuracy bar. General semantic contradictions, freshness, and
superseded-version inference remain unassessed.

Saved-report exports are delivery views over the persisted redacted report snapshot. They do not
re-read raw source documents. Spreadsheet text is emitted as data rather than formulas, HTML has no
network-capable assets, and PDF generation is local. PDF groups repeated rule occurrences into a
bounded review summary; HTML and Excel retain the complete finding list.

Chunk-quality findings describe source or upstream chunk risks, not artifacts introduced by
RAGScanner itself. Generated whitespace/delimiter blocks, normal heading ancestry, and bounded
configured overlap do not become source findings. Naturally short single-chunk documents,
cross-document length differences, and approximate offsets caused by lossless normalization also do
not become source defects.

## Local operation and authentication

The first dashboard targets one user on localhost. Its forms use same-origin CSRF protection and
call local application services; API mutation uses scoped Bearer keys and per-key rate limiting. It
has no public signup, organization, membership, RBAC, SSO, subscription, or entitlement model.
Deployments exposed beyond localhost must use reverse-proxy authentication, VPN, or another
private-network control.

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
