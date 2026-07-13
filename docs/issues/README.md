# GitHub-ready issue drafts

These drafts are ordered by ID, not permission to implement every item concurrently. Milestones and dependencies govern sequencing. Copy each into GitHub only after confirming its Open Decisions and repository placement.

| Range | Milestone |
|---|---|
| RS-001–002 | M0 foundation |
| RS-003–019, RS-027 | M1 Community scanner |
| RS-020–026 | M2 semantic/BYOM |
| RS-028–029 | M3 integration/API |
| RS-030–037 | M4 ücretsiz self-hosted dashboard |
| RS-038–039 | M5 dokümantasyon sitesi |
| RS-040–041 | Kaldırıldı: ödeme ve ücretli dağıtım yok |
| RS-042–045 | Cross-cutting delivery/readiness |
| RS-046–055 | Active Security Scan ve target adapters |
| RS-056 | Multi-platform source compatibility |
| RS-057–060 | Generic target, active runner ve static security orchestration |
| RS-061 | Guided onboarding and consent-based source discovery |

RS-040 ve RS-041 ücretlendirme/kapalı dağıtım işleri olduğu için ürünün tamamen ücretsiz olma kararıyla silinmiştir. Kalan her issue kendi kabul ve doğrulama şartlarını içerir; “done” ayrıca secret içermemeyi, doğru durum belgesini ve güvenlik/gizlilik incelemesini gerektirir.

## Zorunlu uygulama sırası

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

Bu sıra dependency yönüdür; her aşamanın acceptance kriterleri tamamlanmadan sonraki adapter’a geçilmez.
