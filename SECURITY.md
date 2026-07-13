# Güvenlik politikası

## Mevcut durum

Repository scaffold, core kontratlar, active güvenlik bileşenleri, local ingestion pipeline ve ilk deterministic static RAG Security Scan motorunu içerir. Henüz API, dashboard veya worker yoktur. Tam koruma sağlandığı iddia edilmemelidir.

## Scaffold güvenlik ilkeleri

- Gerçek secret, credential, müşteri belgesi veya production raporu Git, fixture, log, issue ve CI’a konmaz.
- `.env.example` yalnız inert yerel değerler içerir; gerçek `.env` Git tarafından dışlanır.
- `ragscanner doctor` ağ bağlantısı kurmaz.
- Harici AI API’si, telemetry, OpenWebUI veya başka remote endpoint yapılandırılmaz.
- Structured logging altyapısı ileride key/content redaksiyonuna uygun tutulur.
- Target/request/response/evaluation/finding/scan domain modelleri raw secret serialization’ını doğrulama hatasıyla reddeder; yalnız opaque external secret reference kabul edilir.
- CI secret scan ve dependency review çalıştırır; testler gerçek cloud credential gerektirmez.
- Gelecekte dosya, parser output, connector response, model output ve report evidence untrusted kabul edilecektir.
- Source descriptor, cursor, health, warning ve error metadata'sı ham credential taşıyamaz; yalnız güvenli secret reference kabul edilir. Kaynak içeriği hassas olabilir ve log/hata/metadata'ya kopyalanmaz. Üretim connector'ları byte limiti, timeout ve async cancellation uygulamalıdır.

## Gelecekteki Security Scan için zorunlu sınırlar

Security rule’ları sürümlü ve testli olmalı; severity ile confidence ayrılmalı; deterministic, heuristic ve LLM-assisted bulgular ayrıştırılmalıdır. Payload/command çalıştırılmamalı, URL otomatik fetch edilmemeli, evidence sınırlandırılıp güvenli biçimde escape/redact edilmelidir.

Active Scan yalnız açık yetkili hedefte, varsayılan non-destructive payload profiliyle çalışmalıdır. SSRF/redirect/DNS rebinding kontrolleri, allowed-host policy, TLS doğrulama, timeout, rate limit, maksimum request/token budget ve cancellation zorunludur. Tool/function çağrısı tetikleyebilecek payload’lar ayrı risk profili ve ikinci onay olmadan gönderilmez. Target response içindeki secret/PII rapora yazılmadan redakte edilir; geniş regex eşleşmeleri tek başına confirmed vulnerability oluşturmaz.

İlk `TargetAdapter` kontratı bu politikayı model seviyesinde somutlaştırır: safe varsayılanı,
açık destructive capability, geçerli/süresi dolmamış authorization, tükenebilir request/süre/hata
bütçesi ve canary/no-op tool testi zorunludur. Observation header/body/citation/source/tool verisi
bounded ve redacted serialize edilir. Bu kontrat transport veya vulnerability evaluation içermez.

İlk active rule pack'ler yalnız non-destructive veri tanımlarıdır. Gerçek credential/e-posta/hedef,
destructive command/SQL, unknown placeholder ve safe olarak yanlış etiketlenen unsafe payload
yükleme sırasında reddedilir. Tool testleri yalnız canary/simulated/no-op davranış ister. Bu
conservative doğrulama tüm tehlikeli metni yakalama garantisi vermez; pack review zorunludur.

Generic REST adaptörü explicit host/port allowlist, DNS IP sınıflandırması, private-network opt-in,
metadata/loopback/link-local blokları, TLS-on default, bounded response ve manuel redirect
doğrulaması uygular. Cross-host redirect credential koruması için bloklanır. Secret header yalnız
resolver portundan alınır. DNS kontrolü ile transport çözümlemesi arasındaki rebinding penceresi
bilinen sınırlamadır.

Response evaluation keyword echo'yu confirmed saymaz; structured action yalnız test case bunu
açıkça unsafe tanımlarsa yüksek güven alır. Control overlap confidence'ı düşürür. Base64/ROT13/
Unicode incelemesi tek katman ve 4 KiB ile sınırlıdır; decoded veri çalıştırılmaz. Evidence bounded,
redacted ve HTML-escaped tutulur. Heuristic sonuçlar kusursuz detection iddiası taşımaz.

Active runner authorization, environment, capability, safe-mode, placeholder, request/duration/
failure budget ve cancellation kapılarını invocation öncesi uygular. Control her case için bir
kez sayılır ve başarısız control finding üretmez. Gerçek authorization actor payload'a konmaz;
sentetik placeholder kullanılır. Partial failure diğer payload'ları varsayılan olarak durdurmaz.

Filesystem connector absolute explicit root'a kilitlidir; filesystem root, traversal, root dışı
symlink ve special file okumayı reddeder. Symlink varsayılan kapalıdır. File/discovery/byte limitleri
ve binary-text ayrımı fail-closed uygulanır. Markdown HTML/code/link yalnız untrusted metindir;
render, execute veya fetch edilmez. Filesystem TOCTOU riski azaltılır fakat tamamen yok edilemez.

PDF parser memory buffer üzerinde text extraction yapar; JavaScript/action çalıştırmaz, link
izlemez, attachment çıkarmaz ve remote resource fetch etmez. Encryption fail-closed reddedilir.
File/page/text/metadata limitleri vardır. Timeout cooperative'dir; native open/page extraction için
process-level preemption henüz yoktur. Image-only PDF warning üretir, OCR yapılmaz.

DOCX parser yalnız memory buffer içindeki OPC/ZIP paketini işler. Parse öncesinde byte, entry,
decompressed-size, XML-part ve compression-ratio limitlerini uygular; traversal ve encrypted ZIP
entry'lerini reddeder. XML incelemesi entity-safe parser kullanır. Macro, OLE/embedded object,
comments, tracked changes, hidden text ve external relationship sinyal olarak raporlanır; hiçbir
active content çalıştırılmaz, embedded içerik çıkarılmaz, URL veya template fetch edilmez. Timeout
cooperative'dir; tek bir native/XML işlemine process-level preemption henüz uygulanmaz. DOCX
görünür metin çıkarımı Word rendering'i değildir; tracked-change ve karmaşık layout fidelity'si
sınırlıdır.

Document normalizer sanitizasyon veya security scanner değildir. Original parsed content'i mutate
etmez; NFC varsayılanıyla multilingual text'i korur. NUL, bidi, zero-width, replacement ve soft
hyphen gibi invisible/control karakterler original'de kalır; normalized görünümde deterministik
marker veya emoji ZWJ için korunmuş karakter ile warning/annotation taşır. Markdown/code/table/
preformatted whitespace conservative korunur. PDF wrap/hyphen repair page, heading, list, table,
URL/path ve code sınırlarında fail-conservative davranır. Boilerplate yalnız candidate olarak
işaretlenir, kaldırılmaz. Ağ, subprocess, render, arbitrary regex veya içerik loglama yoktur.

Document chunker normalization hash/document identity bağını fail-closed doğrular. Şüpheli metni
silmez veya özetlemez; table/code/list hard split'lerini typed warning olmadan yapmaz. Token, input,
block, chunk, overlap, character ve metadata limitleri bounded'dır; maximum chunk aşımında partial
çıktı verilmez. Overlap farklı page/section/heading branch arasında uygulanmaz ve table/code
tekrarında azaltılır. Mapping kayıplıysa açıkça approximate olur. Tokenizer yalnız deterministic
local approximation'dır; network, subprocess, render, link fetch, embedding, LLM veya content
logging yoktur.

Static rule engine yalnız reviewed declarative JSON ve restricted matcher çalıştırır; arbitrary
Python/shell/template/expression yoktur. Riskli regex construct'ları load sırasında reddedilir ve
input bounded'dır. Base64/ROT13/Unicode/hex yalnız strict byte/depth limitinde decode edilir; decoded
veri execute edilmez. URL parse edilir fakat fetch edilmez. Evidence bounded, HTML-escaped ve secret
pattern'lerinde mandatory masked'dır; private key/credential finding serialization'ına ham girmez.
PII varsayılan kapalıdır ve pattern eşleşmesi kimlik kanıtı sayılmaz. Documentation/example/canary
bağlamı finding'i gizlemek yerine confidence/classification düşürür. False negative/positive riski ve
`not detected` durumunun garanti olmadığı belgelenir.

Duplicate ve chunk-quality scanner'ları tamamen yerel, salt-okunur analizdir. Exact grup özeti
kimlik doğrulama amacıyla kullanılmaz ve canonical üye otomatik silme önerisi değildir. Near
duplicate yalnız bounded lexical karşılaştırmadır; semantic eşdeğerlik iddia etmez ve sonuçları
manual review gerektirir. Boilerplate yalnız karşılaştırma imzasından çıkarılır, kaynak metinden
silinmez. Quality evidence bounded, HTML-escaped ve secret-masked'dir; tam içerik loglanmaz.
Belge/chunk/grup/finding/shingle/candidate/time limitleri structured warning üretir. Bu katmanda ağ,
subprocess, render, fetch, embedding, LLM veya detected content execution yoktur.

Credential yalnız environment, OS keychain veya secret-manager reference ile çözülür; config export, finding, artifact veya rapora secret değeri yazılmaz. Safe mode varsayılandır ve kapatılsa bile destructive payload otomatik açılmaz. Tool testleri canary/no-op action kullanır. Active sonuçlar `confirmed`, `probable`, `ambiguous` ve `not_detected` olarak ayrılır.

Reporting engine evidence ve metadata'yı trust boundary'de yeniden redakte eder; private key,
connection string, bearer/API key/cookie, credential URL ve sensitive-key değeri output'a yazılmaz.
Absolute path varsayılan gizlidir. HTML dynamic değerleri escape eder, URL'leri linke çevirmez,
source dosyalarını gömmez ve CSP ile script/connect/default source'u kapatır. External asset,
analytics, network veya subprocess yoktur; limit aşımı sessiz omission değildir.

Unified static pipeline yalnız explicit local root altında read-only connector kullanır. Parser
registry sabittir; config dynamic import, code execution veya environment interpolation yapmaz.
TXT/Markdown binary kontrolü sürer; PDF/DOCX bytes yalnız bounded parser'a gider. Per-file stage
failure diğer dosyalara içerik taşımaz. Error/log/event mesajları full content/evidence içermez ve
source root maskelenir. Report write aynı dizinde temporary file ve atomic replace kullanır;
overwrite ve parent creation varsayılan kapalıdır.

Tek dosya scan parent directory'yi root olarak kullanır fakat exact filename allowlist uygular;
komşu dosyaları örtük discover etmez. Single-source modu tek başına warning değildir. File/page,
extracted/normalized character ve chunk limitleri config ile bounded'dır; limit aşımı typed
skip/error ve partial/failed status üretir, content execution veya uncontrolled growth sağlamaz.

## Güvenlik bildirimi

Bir güvenlik açığı bildirmek için public issue açmayın. Canonical repository'nin
[Security Advisories](https://github.com/atakaneser/RAGScanner/security/advisories/new) sayfasından
özel taslak advisory oluşturun. Gerçek secret, exploit payload'ı, müşteri belgesi veya production
raporunu issue, discussion ya da pull request'e eklemeyin.

Henüz public stable sürüm yoktur. `0.1.0a1` teknik alpha için best-effort güvenlik düzeltmesi
sağlanır; eski alpha snapshot'ları için backport garantisi verilmez.
