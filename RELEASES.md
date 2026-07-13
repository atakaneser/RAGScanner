# Release strategy

Henüz yayınlanmış sürüm yoktur. Hazırlanan ilk aday PEP 440 `0.1.0a1`, public release başlığı
`v0.1.0-alpha.1` olacaktır. Apache-2.0 lisansı, canonical repository ve GitHub Security Advisory
bildirim kanalı onaylanmıştır; reviewed clean commit ve release doğrulamaları tamamlanmadan tag veya
package publish yapılmaz. İlk sürümden itibaren public API/report/SDK sözleşmeleri Semantic
Versioning, changelog ve açık release notes ile yönetilir. Rule pack, report schema, fingerprint,
scoring policy ve connector compatibility ayrıca sürümlenir.

## Dağıtım

- Public Python package, açık container image ve dokümantasyon protected `main` üzerinden yayınlanır.
- Dashboard/API/worker’lar aynı açık repository ve uyumluluk setinde kalır.
- Core → CLI/API/worker/dashboard contract testleri → public artifact sırası izlenir.
- Güvenlik düzeltmeleri gerektiğinde yayından önce koordineli özel disclosure uygulanabilir; düzeltilen kod yine herkese açık yayınlanır.

Yayın öncesi test, package install, schema compatibility, SBOM/provenance, supported-platform matrisi, upgrade/rollback ve bilinen sınırlamalar gözden geçirilir. Yayın yalnızca açık kullanıcı onayıyla yapılır.
