# Active security test library

RAGScanner'ın active test library'si, gelecekte `TargetAdapter` üzerinden taşınabilecek
deterministik veri tanımlarını içerir. Test case'ler payload çalıştırmaz, ağ çağrısı yapmaz ve
response değerlendirmez. Hedef sahibinin açık yetkilendirmesi her active scan için zorunludur.

## Format ve sürümleme

Paketler `rules/active/*.json` altında JSON olarak tutulur. JSON seçimi yeni YAML bağımlılığı
gerektirmediği, standart kütüphaneyle deterministik ayrıştırıldığı ve yayınlanan JSON Schema ile
aynı temsili kullandığı için seçildi. Pack schema, pack ve test case ayrı semantik sürüm taşır.
Desteklenmeyen schema sürümü fail-closed reddedilir. Schema
`rules/schemas/active_test_case.schema.json` dosyasındadır; çalışma zamanı doğrulamasını typed
Pydantic modelleri ve ek güvenlik validator'ları yapar.

## Güvenlik politikası

Safe mode varsayılandır. `safe_for_production`, payload'ın gerçek credential, gerçek hedef,
gerçek e-posta, destructive komut/SQL veya amaçlanan gerçek yan etki içermediğini belirtir;
payload'ın risksiz olduğunu ya da hedefin güvenli olduğunu garanti etmez. Unsafe işaretli payload
safe olarak yayınlanamaz. Destructive içerik ilk library'de işaretine bakılmadan reddedilir.
Tool/function testleri yalnız canary, dry-run, simulated veya no-op davranış kullanır.

High ve critical test case'ler kontrol payload'ı taşır. Kontroller generic refusal, keyword
eşleşmesi, genel helpfulness ve gerçek güvenlik davranışını ayırmaya yardımcı olur; tek başına
vulnerability kanıtı değildir. False positive hâlâ mümkündür ve değerlendirme ayrı katmandadır.

Evaluation engine indicator string'lerini bounded DSL olarak yorumlar; prefix ve precedence
kuralları [`response-evaluation-engine.md`](response-evaluation-engine.md) içindedir. Katkılar
plain-language indicator yerine mümkün olduğunda explicit `exact:`, `field:`, `tool:` veya
`function:` contract'ı kullanmalıdır.

## Placeholder kuralları

Yalnız `CANARY_TOKEN`, `TEST_SESSION_ID`, `SAFE_TOOL_NAME`, `FAKE_DOCUMENT_NAME` ve
`AUTHORIZED_TEST_USER` kabul edilir. Template motoru yoktur; renderer yalnız açık string
replacement yapar. Tanımsız, eksik, fazla veya iç içe placeholder fail-closed reddedilir.

## Katkı rehberi

Yeni pack küçük ve belirli bir kategoriye odaklanmalı; stable benzersiz ID, semver, beklenen
güvenli davranış, unsafe/safe/ambiguous göstergeler, remediation, dil ve tag bilgisi içermelidir.
Payload gerçek kişi/sistem/veri hedeflememeli ve executable içerik taşımamalıdır. High/critical
case için pratik bir kontrol eklenmeli; Türkçe/İngilizce ve boundary testleriyle birlikte
gönderilmelidir. Conservative validator kusursuz tehlikeli içerik tespiti iddiasında değildir.
