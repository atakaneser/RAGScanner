# Active security scan runner

`ActiveSecurityScanRunner`, versioned active test library, provider-neutral `TargetAdapter` ve
response evaluator arasında yalnız in-memory orchestration yapar. Persistence, report, API, UI,
distributed worker veya retry içermez.

## Lifecycle ve seçim

Plan doğrulamasından sonra target descriptor ve authorization kontrol edilir; scan `running`
olur. Test case/payload seçimi ID, kategori, tag, dil, enabled, retrieval/tool capability,
safety-mode ve production-safe durumuna göre stable ID sırasıyla yapılır. Uyumsuz testler
structured `test_skipped` event'i ve bounded warning üretir.

Terminal durumlar:

- `completed`: seçili execution'lar uyarısız tamamlandı.
- `completed_with_warnings`: skip, kısmi hata veya budget sınırı oluştu.
- `failed`: başlayan execution'ların tamamı başarısız oldu veya runner-level error kaydedildi.
- `cancelled`: açık iptal istendi; mevcut invocation adapter cancellation'a iletildi.

Authorization/config hatası invocation öncesinde fail-closed sonuçlanır. Tek payload, control,
adapter veya evaluator hatası varsayılan olarak diğer testleri bozmaz.

## Güvenlik kapıları ve placeholder

Safe mode varsayılandır. Expired/missing target-owner authorization reddedilir. Production target
yalnız safe mode kabul eder. Destructive test hem explicit destructive plan hem target capability
ister; safe mod production-unsafe payload çalıştırmaz. Retrieval ve tool/function testleri target
capability bildirmiyorsa atlanır.

Renderer yalnız library allowlist'ini kullanır. Runtime değerleri synthetic canary, session,
no-op tool, fake document, synthetic authorized user ve target adıdır. Authorization actor,
credential veya kişisel veri payload'a kopyalanmaz. Bilinmeyen placeholder invocation öncesinde
yalnız ilgili payload'ı fail-closed atlar.

## Control ve budget

Control açıksa her test case için en fazla bir kez güvenli control çalıştırılır ve aynı case'in
payload varyantlarıyla karşılaştırılır. Control request budget'a dahildir. Başarısız control
vulnerability finding üretmez ve attack sonucu control'süz değerlendirilir.

Request, süre ve failure threshold kontrolleri control/attack öncesinde ve request sonrasında
yapılır. Adapter'ın timeout, delay, rate limit ve kendi budget kontrolleri ayrıca geçerlidir.
Otomatik retry yoktur. İlk sürüm `concurrency=1` ile deterministik ordering ve burst önleme sağlar.

## Finding politikası

`confirmed` ve `probable` finding üretir. `ambiguous` yalnız planın manual-review retention
politikası açıksa tutulur. `not_detected` ve transport kaynaklı `inconclusive` vulnerability
finding üretmez. Severity test case'den, confidence evaluator'dan gelir; classification
yükseltilmez. Finding target/test/execution referansı, bounded evidence, remediation ve canonical
stable fingerprint taşır.

## Event akışı

Provider-neutral async event sink; scan start, selection/skip, control, invocation, evaluation,
finding, warning, cancellation ve completion event'lerini alır. No-op sink varsayılandır. Event
sink hatası scan'i durdurmaz; WebSocket, FastAPI veya database bağımlılığı yoktur.

Bilinen sınırlar: yalnız sequential execution, in-memory sonuç, process restart recovery yok,
distributed cancellation yok ve score üretilmiyor.
