# GitHub-ready issue drafts

Drafts are ordered by ID; this is not permission to implement them concurrently. Milestones and
dependencies control sequencing. Copy a draft to GitHub only after confirming its open decisions
and repository placement.

| Range | Milestone |
|---|---|
| RS-001–002 | M0 foundation |
| RS-003–019, RS-027 | M1 community scanner |
| RS-020–026 | M2 semantic analysis and BYOM |
| RS-028–029 | M3 integration and API |
| RS-030–037 | M4 free self-hosted dashboard |
| RS-038–039 | M5 documentation site |
| RS-040–041 | Removed: no payment or paid distribution |
| RS-042–045 | Cross-cutting delivery and readiness |
| RS-046–055 | Active Security Scan and target adapters |
| RS-056 | Multi-platform source compatibility |
| RS-057–060 | Generic target, active runner, and static security orchestration |
| RS-061 | Guided onboarding and consent-based source discovery |
| RS-062 | Reporting usability and canonical project language |

RS-040 and RS-041 were removed after the decision to keep the complete product free and open
source. Each remaining issue contains its own acceptance and verification conditions. “Done” also
requires no committed secrets, an accurate status document, and security/privacy review.

## Required implementation direction

1. [RS-004 Core domain models](RS-004-core-models.md)
2. [RS-059 Static SourceConnector contract](RS-059-static-source-connector-contract.md)
3. [RS-046 TargetAdapter contract](RS-046-target-adapter-contract.md)
4. [RS-047 Safe payload/test-case model](RS-047-active-payload-pack.md)
5. [RS-057 Generic REST target adapter](RS-057-generic-rest-target-adapter.md)
6. [RS-053 OpenAI-compatible target adapter](RS-053-openai-compatible-target.md)
7. [RS-052 Response evaluation engine](RS-052-active-response-analyzer.md)
8. [RS-058 Active Security Scan runner](RS-058-active-security-scan-runner.md)
9. [RS-060 Static document Security Scan](RS-060-static-document-security-scanner.md)
10. [RS-018/019/055 Reports](RS-018-terminal-json-reports.md)
11. [RS-028 OpenWebUI connector](RS-028-openwebui-connector.md)
12. [RS-054/056 Additional platform adapters](RS-056-multi-platform-source-connectors.md)

This list describes dependency direction. An adapter may not advance until the acceptance criteria
for its prerequisites are satisfied.
