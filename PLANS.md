# Plans and open decisions

RAGScanner is one free and open-source product. There is no Community/Pro split, payment,
subscription, entitlement, or commercial package decision.

| ID | Open decision | Blocks |
|---|---|---|
| OD-001 | **Resolved:** Apache-2.0; see `LICENSE_DECISION.md` | — |
| OD-002 | Package name and single-repository module layout | RS-003 |
| OD-003 | Default retention and cleanup for local history | RS-016 |
| OD-005 | Health score formula, critical-security cap, coverage, and calibration | RS-017 |
| OD-006 | RAG Rot baseline/window and missing-data behavior | RS-027 |
| OD-007 | SQLAlchemy or SQLModel | RS-004/016 |
| OD-008 | Self-hosted queue/scheduler technology and minimum topology | RS-035 |
| OD-009 | Optional multi-user authentication/session model; local mode remains unauthenticated | RS-030 |
| OD-010 | Connector secret references, encryption, and key rotation | Connectors |
| OD-011 | Evidence/artifact retention, deletion, and optional object storage | Monitoring/privacy |
| OD-012 | Supported OpenWebUI versions and change-detection fallback | RS-028 |
| OD-013 | Model-provider compatibility contract and offline model packaging | M2 |
| OD-014 | Notification channels and retry/deduplication policy | RS-036 |
| OD-016 | Whether signed reports are required and what a signature would prove | Reporting |
| OD-017 | Whether telemetry is always disabled or available through explicit opt-in | Release |
| OD-018 | Security contact, supported versions, and disclosure policy | Public release |
| OD-019 | Accessibility and browser support target | Dashboard/docs |
| OD-021 | API/OpenWebUI module placement in the monorepo | M3 |
| OD-022 | Rule-pack format, signing, update, and rollback | M1/M4 |
| OD-023 | Relationship between single-user and optional organization models | RS-030 |
| OD-024 | Source/chunk identity across connector changes | RS-004/006/028 |
| OD-025 | Parser resource limits and isolation strategy | Parser work |
| OD-026 | Default Active Scan safety profile and destructive-test policy | Active Security Scan |
| OD-027 | Generic TargetAdapter request/response/capability contract | RS-046 |
| OD-028 | Tier 1/2/Experimental compatibility criteria and version matrix | Connectors/targets |
| OD-029 | Active response calibration data and result semantics | Active Security Scan |
| OD-030 | OpenAI Responses versus Chat Completions target priority | OpenAI adapter |

## Current delivery sequence

1. Complete RS-062 usability and canonical-language migration.
2. Resolve OD-003 and OD-007 for SQLite scan history and migrations.
3. Implement application services, API, and the durable local job worker.
4. Resolve OD-010, OD-012, OD-021, and OD-024 before the production OpenWebUI connector.
5. Resolve OD-019 before dashboard acceptance and browser QA.

Preserve the vertical slice: safe input → normalized document → security/quality finding →
versioned report → optional persistence/application delivery. Later adapters must not add provider
conditionals or database/UI dependencies to Core.
