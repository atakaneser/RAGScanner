# License decision

**Karar:** Repository sahibi 13 Temmuz 2026 tarihinde tüm RAGScanner repository'si için
Apache License 2.0 kullanımını onayladı. Kök [`LICENSE`](LICENSE) dosyası kaynak kodu,
CLI'ı, rule pack'leri, dokümantasyonu ve gelecekteki ücretsiz ürün bileşenlerini kapsar.

Amaç tüm ürünü—core, CLI, dashboard, scheduler, connector ve güvenlik rule’ları dahil—ücretsiz ve katkıya açık tutmaktır. Ücretli özellik sınırı veya kapalı modül olmayacaktır.

| Seçenek | Avantaj | Risk |
|---|---|---|
| Apache-2.0 | Basit, izin verici, patent grant içerir | Üçüncü taraf ticari kullanımına izin verir |
| MPL-2.0 | Dosya seviyesinde değişikliklerin açık kalmasını ister | Lisans uyumu daha karmaşıktır |
| AGPL-3.0 | Ağ üzerinden sunulan değişiklikleri de korur | Benimsenme ve entegrasyon sürtünmesi yaratabilir |

Apache-2.0; izin verici yeniden kullanım, katkılar için açık patent grant'i ve geniş ekosistem
uyumluluğu nedeniyle seçildi. Bu karar ücretli sürüm veya kapalı modül oluşturmaz. Apache-2.0
trademark hakkı vermediği için ayrı bir trademark politikası ancak gerçekten gerekirse hazırlanır.
