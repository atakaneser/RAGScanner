# ADR-0001: Tek açık kaynak repository

- Status: Proposed
- Date: 2026-07-12

## Context

RAGScanner’ın bütün geliştirmesi ücretsiz olacaktır. Ücretli sürüm, kapalı kaynak modül, entitlement veya özellik kısıtı olmayacaktır.

## Decision

Core, CLI, SDK, API, worker, OpenWebUI connector, dashboard, scheduler, güvenlik rule’ları ve dokümantasyon tek bir açık repository içinde modüler olarak geliştirilecektir. Core yine UI, connector, model sağlayıcısı ve veritabanı adaptörlerinden bağımsız kalır.

## Consequences

Katkı, issue takibi, sürümleme ve güvenlik güncellemeleri sadeleşir. Repository büyüdükçe path-based CI ve net modül sahipliği gerekir. Dokümantasyon sitesi aynı repodan yayınlanabilir; ayrı deploy projesi yalnızca teknik gerekçeyle düşünülebilir.

