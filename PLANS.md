# Plans and open decisions

RAGScanner is one free and open-source product. There is no Community/Pro split, payment,
subscription, entitlement, or commercial package decision.

| ID | Open decision | Blocks |
|---|---|---|
| OD-001 | **Resolved:** Apache-2.0; see `LICENSE_DECISION.md` | — |
| OD-002 | Package name and single-repository module layout | RS-003 |
| OD-003 | **Resolved:** explicit opt-in, no automatic deletion; see ADR-0019 | — |
| OD-005 | Health score formula, critical-security cap, coverage, and calibration | RS-017 |
| OD-006 | RAG Rot baseline/window and missing-data behavior | RS-027 |
| OD-007 | **Resolved:** SQLAlchemy Core plus packaged Alembic migrations; see ADR-0019 | — |
| OD-008 | **Resolved:** SQLite durable queue, one worker, and an idempotent interval materializer; see ADR-0007/0021/0034 | — |
| OD-009 | Optional multi-user authentication/session model; initial local API-key/CSRF composition is resolved by ADR-0022 | RS-030 |
| OD-010 | Connector secret references, encryption, and key rotation | Connectors |
| OD-011 | Evidence/artifact retention, deletion, and optional object storage | Monitoring/privacy |
| OD-012 | Supported OpenWebUI versions and change-detection fallback | RS-028 |
| OD-013 | Model-provider compatibility contract and offline model packaging | M2 |
| OD-014 | Notification channels and retry/deduplication policy | RS-036 |
| OD-016 | Whether signed reports are required and what a signature would prove | Reporting |
| OD-017 | Whether telemetry is always disabled or available through explicit opt-in | Release |
| OD-018 | Security contact, supported versions, and disclosure policy | Public release |
| OD-019 | Accessibility and browser support target | Dashboard/docs |
| OD-021 | **Resolved for initial API:** packaged application/API modules; see ADR-0020 | — |
| OD-022 | Rule-pack format, signing, update, and rollback | M1/M4 |
| OD-023 | Relationship between single-user and optional organization models | RS-030 |
| OD-024 | Source/chunk identity across connector changes | RS-004/006/028 |
| OD-025 | Parser resource limits and isolation strategy | Parser work |
| OD-026 | Default Active Scan safety profile and destructive-test policy | Active Security Scan |
| OD-027 | Generic TargetAdapter request/response/capability contract | RS-046 |
| OD-028 | Tier 1/2/Experimental compatibility criteria and version matrix | Connectors/targets |
| OD-029 | Active response calibration data and result semantics | Active Security Scan |
| OD-030 | OpenAI Responses versus Chat Completions target priority | OpenAI adapter |
| OD-031 | Capability tiers and priority for document, web, SaaS, object-store, and vector sources | RS-056/063 |
| OD-032 | Website/sitemap crawl bounds, robots behavior, authentication, and change identity | Web connector |
| OD-033 | SharePoint/OneDrive Graph permissions, site/drive/list identity, and delta tokens | SharePoint connector |

## Current delivery sequence

1. Complete the remaining RS-016 recovery/concurrency and RS-033/034 filter/scale acceptance.
2. Complete remaining API-scale persistence, artifact retention, and worker recovery acceptance.
3. Resolve OD-010, OD-012, and OD-024 before incremental OpenWebUI synchronization and broader
   credential providers.
4. Define and implement the RS-056/063 capability matrix for SharePoint, websites, SaaS knowledge systems, Git,
   object stores, vector databases, and unknown RAG environments.
5. Resolve OD-019 and extend the initial dashboard with scan detail, comparison, connector settings,
   scheduling, and the supported accessibility/browser matrix.

Preserve the vertical slice: safe input → normalized document → security/quality finding →
versioned report → optional persistence/application delivery. Later adapters must not add provider
conditionals or database/UI dependencies to Core.
