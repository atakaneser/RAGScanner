# Mimari

## Nihai öneri

İlk desteklenen mimari **Option A: Python modüler monolith** olacaktır:

- Python 3.12+
- Framework’ten bağımsız scanner core
- Typer CLI
- FastAPI HTTP API
- Jinja2 + HTMX/az miktarda vanilla TypeScript ile server-rendered dashboard
- SQLite + WAL
- Aynı kod tabanını kullanan basit database-backed worker
- Worker içinde APScheduler ile schedule enqueue etme
- Tek public monorepo
- Yerel süreçler veya Docker Compose ile tek makine/VPS kurulumu

Bu karar microservice değildir. API ve worker ayrı process olarak çalışabilir ancak aynı Python paketi, aynı SQLite veritabanı ve aynı artifact dizinini paylaşır. İlk sürümde Redis, RabbitMQ, Celery, Kubernetes, PostgreSQL, Next.js, organization veya auth zorunluluğu yoktur.

## Option A ve Option B karşılaştırması

| Ölçüt | Option A: Python + Jinja/HTMX | Option B: Python API + Next.js |
|---|---|---|
| Geliştirme hızı | Tek dil/backend contract, daha hızlı | İki toolchain ve API client ek işi |
| Bakım | Tek dependency graph ve release | Python/Node güvenlik ve sürüm bakımı |
| Deployment | API/web tek image; worker aynı image | En az web + API + worker image |
| UI kalitesi | Veri yoğun dashboard için yeterli | Karmaşık etkileşimlerde daha güçlü |
| Type sharing | Pydantic modeller doğrudan template/view model üretir | OpenAPI’den TS üretimi ve uyumluluk testi gerekir |
| Docker karmaşıklığı | Düşük | Orta |
| Kaynak kullanımı | Düşük; Node runtime yok | Daha yüksek RAM/disk/build maliyeti |
| Gelecekte genişleme | HTMX sınırına kadar yeterli; API zaten mevcut | Büyük frontend ekibi/çok etkileşimli UI için daha iyi |

RAGScanner’ın ilk dashboard’u scan listesi, finding filtreleri, progress, karşılaştırma, schedule ve configuration ekranlarından oluşur. Bu ihtiyaçlar SPA gerektirmez. UI karmaşıklığı somut olarak arttığında Next.js ayrı bir ADR ile yeniden değerlendirilebilir.

## Repository yapısı

```text
ragscanner/
├── apps/
│   ├── api/                 # FastAPI composition root ve HTTP routes
│   ├── web/                 # Jinja templates, HTMX, static assets
│   └── worker/              # job claim, scheduler ve scan runner
├── packages/
│   ├── scanner/             # domain, orchestration, parser/scanner portları
│   ├── connectors/          # filesystem, OpenWebUI, gelecekte diğerleri
│   ├── targets/             # aktif test için RAG/chat endpoint adapter’ları
│   ├── providers/           # opsiyonel analiz modeli adapter’ları
│   ├── security_rules/      # ücretsiz versioned rules ve metadata
│   └── shared/              # config, DB adapter, logging, common schemas
├── docs/
├── examples/                # yalnızca sentetik knowledge base’ler
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── fixtures/
└── deployments/
    └── compose/
```

Başlangıçta tek Python distribution tercih edilir. Dizinler dependency sınırıdır; ayrı PyPI paketleri ancak gerçek bağımsız sürüm ihtiyacı doğarsa oluşturulur.

## Dependency sınırları

```text
CLI / FastAPI / Web / Worker
             |
     application services
             |
scanner domain + ports + rule contracts
       ^              ^
connectors/parsers   storage/model/report adapters
```

- `scanner` FastAPI, Typer, Jinja, SQLite, OpenWebUI SDK veya model vendor import etmez.
- `security_rules`, scanner rule contract’ına bağlıdır; UI veya storage bilmez.
- `connectors`, neutral document/chunk/source modelleri üretir.
- `targets`, neutral active-test request/response sözleşmesini uygular; scanner rule’larını bilmez.
- `providers`, yalnız opsiyonel analiz modelini sunar; taranan hedef ile otomatik eşleştirilmez.
- `shared` domain business rule içermez; çapraz bağımlılık çöplüğüne dönüşmez.
- `apps/*` yalnızca composition ve delivery yapar.
- Dashboard core fonksiyon çağırmaz; application service kullanır.

Framework-bağımsız core domain kontratları `ragscanner.domain` altında uygulanmıştır. Static, active ve shared modeller ile saf fingerprint/redaksiyon helper’ları network, filesystem, database veya delivery framework import etmez.

## Veri depolama: SQLite seçimi

İlk sürüm için SQLite seçilir:

- tek kullanıcı/tek makine hedefiyle uyumludur,
- ek database servisi ve yönetimi gerektirmez,
- scan history, finding, occurrence, document, chunk, schedule, connector config ve score snapshot hacmini karşılar,
- backup ve taşınabilirliği basittir.

WAL, busy timeout, kısa transaction, tek aktif writer/worker ve batch write kullanılır. Büyük raw document/artifact blob’ları DB’ye konmaz; content-addressed yerel artifact dizininde tutulur. DB yalnızca metadata/reference taşır.

PostgreSQL şu kanıtlardan biri oluşursa yeniden değerlendirilir: birden fazla eşzamanlı worker gereksinimi, sürekli write contention, uzaktan birden çok kullanıcı, yüksek hacimli API deployment veya ölçülen SQLite limitleri. Storage portları ve SQLAlchemy/Alembic migration’ları bu geçişi mümkün kılar; ancak PostgreSQL uyumluluğu ilk sürümde test yükü değildir.

### Basit veri modeli

- `KnowledgeBase`
- `Connector` ve secret olmayan config; secret değer ayrı environment/file reference
- `ScanSchedule`
- `Scan`
- `ScanArtifact`
- `Document`
- `Chunk`
- `Finding`
- `FindingOccurrence`
- `FindingStatusHistory`
- `ScoreSnapshot`
- `RulePack` ve `RuleVersion`
- `Job`

`User`, `Organization`, `Membership`, `Subscription`, `Entitlement` ve payment modelleri yoktur.

## Background job kararı

| Seçenek | Değerlendirme |
|---|---|
| FastAPI in-process task | Process restart’ında kayıp; uzun scan/cancel için uygun değil |
| Yalnız APScheduler | Schedule üretir fakat dayanıklı job execution sağlamaz |
| RQ | Redis servisi ekler; ilk tek makine sürümü için gereksiz |
| Celery | Güçlü fakat broker/result backend ve yüksek operasyon yükü getirir |
| Dramatiq | Celery’den hafif ama yine broker gerekir |
| Database-backed worker | Mevcut SQLite ile durable, görünür ve yeterince basit |

Seçim: `Job` tablosunu kullanan tek worker. Worker transaction içinde queued job’ı lease/claim eder, progress ve heartbeat yazar, cancel flag’i kontrol eder. APScheduler yalnızca due schedule’lardan idempotent job üretir ve worker process içinde çalışır. Scan effect’leri job ID/idempotency key ile tekrar güvenli olmalıdır.

## Yerel geliştirme topolojisi

```text
browser -> FastAPI/Jinja :8000
CLI -----------|          |
               |       SQLite (WAL)
worker + APScheduler -----|
               |
      local artifact/model cache
```

API ve worker ayrı terminal process’i olabilir. CLI doğrudan scanner application service’i çalıştırabilir veya `--server` modu ileride API’ye istek atabilir. İlk CLI için doğrudan yerel çalışma tercih edilir.

## Docker Compose topolojisi

```text
browser
  |
ragscanner-app (FastAPI + Jinja)
  |            \
  |             shared data volume: SQLite + artifacts
  |            /
ragscanner-worker (aynı image, farklı command; APScheduler dahil)
```

Yalnız iki service zorunludur ve aynı image kullanılır. Reverse proxy opsiyoneldir. Dashboard localhost dışına publish ediliyorsa VPN/private network veya reverse-proxy auth zorunlu olarak belgelenir. OpenWebUI ve kullanıcı LLM’i dış servislerdir; Compose’a zorunlu eklenmez.

## Veri akışları

### Yerel klasör taraması

CLI veya dashboard scan request oluşturur → filesystem connector root sınırlarıyla dosyaları enumerate eder → parser izolasyon/limitlerle document üretir → normalize/chunk → security ve health rules → finding/occurrence/score → SQLite ve rapor artifact.

Uygulanmış ingestion bölümü root-confined TXT/Markdown discovery, bounded raw content ve saf
TXT/Markdown/PDF/DOCX → `Document` parsing'dir. PDF parser page-offset map; DOCX parser
ordered structure block ve offset metadata'sı üretir. OCR yoktur. DOCX ZIP/XML preflight ve
bounded in-memory extraction uygular; active/embedded content çalıştırılmaz veya çıkarılmaz,
external relationship izlenmez.
Parser sonrası framework-bağımsız normalizer original content'i koruyarak versioned normalized
text, hash, structured annotation ve bounded source-mapping segmentleri üretir. Unicode/whitespace
ve PDF repair aşamaları explicit config/provenance taşır; boilerplate kaldırılmaz. Framework-bağımsız
chunker normalization segmentlerini tüketir; structure, paragraph veya token-window stratejisiyle
stable `Chunk` üretir ve forced split/overlap/mapping provenance'ını taşır. Scanner/persistence
yoktur. Connector port arkasında parser, normalizer ve chunker transporttan bağımsızdır.

Framework-bağımsız quality katmanı aynı immutable çıktıları tüketir. `ExactDuplicateScanner`
normalized SHA-256 ile belge/chunk grupları; `NearDuplicateScanner` bounded lexical shingle candidate
index ve Jaccard/containment ile review-required gruplar; `ChunkQualityScanner` boyut, yapı, yoğunluk,
overlap, mapping ve extraction sinyalleri üretir. Servisler storage/model bilmez, content mutate veya
otomatik delete etmez. Quality score ürün tanımlı heuristic'tir; retrieval başarısı kanıtı değildir.

İlk static security scanner bu pipeline'ın `Document`, normalized result, `Chunk`, parser warning,
annotation ve metadata çıktılarını framework-bağımsız biçimde tüketir. Versioned JSON rule pack →
restricted matcher → context/FP adjustment → bounded/redacted evidence → stable `Finding` akışıdır.
File loading ve CLI composition dış sınırdadır; core network, storage, model veya UI bilmez.

Uygulanan `StaticScanPipeline`; filesystem discovery/read, explicit parser registry,
normalization/chunking, static security, exact/near duplicate, chunk quality, assessed-only scoring
ve report-ready aggregate'i tek framework-bağımsız orchestration akışında birleştirir. Dosya stage
hataları izole; collection scanner hataları bağımsız; event sink provider-neutral'dır. CLI yalnız
composition, local TOML override, exit policy ve atomic report write sağlar.

### OpenWebUI taraması

Kullanıcı connector endpoint ve secret reference yapılandırır → connector capability/version kontrol eder → seçili knowledge base’i sayfalı ve idempotent senkronize eder → neutral document/chunk modelleri → aynı scanner pipeline. Core OpenWebUI bilmez.

### Scheduled scan

APScheduler due schedule’ı bulur → benzersiz schedule occurrence key ile `Job` ekler → worker claim eder → config snapshot ile scan başlatır → heartbeat/progress → completion/failure ve sonraki run bilgisi.

### Security scan

Parser raw ve normalize görünümü korur → deterministic rules → bounded decode/hidden text/secret/URL/command heuristics → adaylar detection class ve confidence ile finding’e dönüşür → opsiyonel LLM-assisted doğrulama ayrı aşama → redakte evidence ve remediation raporu.

### Active security scan

Kullanıcı yetkili target ve test policy seçer → payload pack capability/risk filtresinden geçer → `TargetAdapter` rate limit/timeout/budget ile isteği gönderir → ham cevap bounded/redacted artifact olur → deterministic response analyzer önce çalışır → belirsiz sonuç opsiyonel evaluator’a gider → finding payload/target/analyzer sürümü ve request correlation ile kaydedilir. Target adapter hiçbir zaman source connector veya model provider olarak örtük kullanılmaz.

Response evaluation artık transport'tan ayrı saf katmandır: deterministic indicator, bounded
heuristic, control comparison ve explicit merge precedence uygular. Opsiyonel LLM evaluator yalnız
porttur. Ayrıntılar [`docs/response-evaluation-engine.md`](docs/response-evaluation-engine.md)
içindedir.

Active runner bu portları concurrency=1 ile in-memory orkestre eder: deterministic selection →
opsiyonel tek control → attack invocation → evaluation → execution/finding → terminal scan.
Event sink provider-neutral, persistence dışarıdadır. Ayrıntılar
[`docs/active-scan-runner.md`](docs/active-scan-runner.md) içindedir.

İlk active test library JSON ve semver kullanır. Core loader yalnız supplied text/bytes ayrıştırır;
onaylı yerel dosyaları okumak ayrı ince adaptördür. Test case tanımları executable logic içermez,
unknown placeholder veya destructive içerik fail-closed reddedilir. Ayrıntılar
[`docs/active-security-test-library.md`](docs/active-security-test-library.md) içindedir.

## Adapter sözleşmeleri ve uyumluluk seviyeleri

- `SourceConnector`: Document, chunk, metadata veya knowledge-base içeriği okur. İlk vendor-neutral async port; descriptor/capability, sayfalı item/content okuma, değişiklik algılama, sağlık ve typed hata sözleşmelerini sağlar. Filesystem, OpenWebUI, Qdrant ve Chroma gelecekteki örneklerdir. Aktif saldırı isteği göndermez ve analiz modeli sağlamaz. Ayrıntılı kontrat: [`docs/source-connector-contract.md`](docs/source-connector-contract.md).
- `TargetAdapter`: Hedef sahibinin açıkça yetkilendirdiği çalışan RAG/LLM uygulamasına black-box güvenlik test isteği hazırlar ve taşır. Vendor-neutral async port; capability, health, prepare/invoke, bütçe, cancellation ve opsiyonel session/model-discovery sözleşmelerini sağlar. Generic REST, OpenAI-compatible chat, OpenWebUI chat ve Hugging Face inference endpoint gelecekteki örneklerdir. Document kaynağı değildir ve vulnerability değerlendirmez. Ayrıntılar: [`docs/target-adapter-contract.md`](docs/target-adapter-contract.md).
- `ModelProvider`: RAGScanner’ın kendi opsiyonel gelişmiş analizinde kullanacağı chat veya embedding modelini sağlar. Structured-output ve locality/privacy metadata taşır. Ollama, OpenAI-compatible model ve OpenWebUI model endpoint örnektir. Taranan target değildir ve retrieval varlığını kanıtlamaz.

Bu roller aynı platform tarafından sağlansa bile ayrı configuration, credential reference, consent ve provenance kullanır. Credential değeri domain modeline veya rapora yazılmaz; yalnız güvenli secret reference tutulur.

Bir LLM endpoint’i RAG sistemi olmak zorunda değildir. OpenAI veya Hugging Face kullanılması retrieval yapıldığını kanıtlamaz. Bir target yalnız test edilen uygulamanın gerçekten document/vector/index retrieval yaptığı doğrulandığında `rag` target olarak etiketlenir; aksi halde `llm` veya `unknown_retrieval` target’tır. Retrieval capability bilinmiyorsa RAG-specific testler `not_assessed` olur.

Framework-bağımsız reporting katmanı `Scan`, `Finding`, execution, score ve scanner aggregate'lerini
salt okunur tüketir. Son-sınır redaksiyon ve deterministic view-model ardından terminal, versioned
JSON veya standalone escaped HTML adapter'ına gider. Reporting database, FastAPI/Jinja, connector,
target veya model provider import etmez; HTML external asset/network kullanmaz.

Response evaluation sonucu tam olarak şu durumlardan biridir:

- `confirmed`: Kontrollü canary, structured tool event veya tekrar üretilebilir güçlü kanıt var.
- `probable`: Birden fazla açıklanabilir sinyal var fakat doğrudan doğrulama yok.
- `ambiguous`: Kanıt hem güvenli hem riskli açıklamayla uyumlu.
- `not_detected`: Test koşullarında risk sinyali görülmedi; güvenlik garantisi değildir.

Uyumluluk üç seviyede yayınlanır:

- **Tier 1:** CI’da contract fixture ve resmi supported-version matrix.
- **Tier 2:** Generic protocol üzerinden beklenen uyumluluk; community doğrulaması gerekir.
- **Experimental:** API kararsız veya yalnız manuel fixture ile doğrulanmış.

İlk concrete `TargetAdapter` generic REST olacaktır; bunun üstüne OpenAI-compatible protokol adapter’ı gelir. Platform adapter’ları yalnız auth, endpoint discovery, payload/response mapping ve capability farklılıklarını taşır. Core’da `if provider == ...` dalları bulunmaz.

Generic REST adaptörü async `httpx` kullanır. Declarative template/dotted mapping, secret resolver
portu, enjekte edilebilir DNS doğrulaması, manuel redirect ve bounded streaming concrete
`ragscanner.targets` sınırındadır; core domain HTTP bağımlılığı almaz. Ayrıntılar
[`docs/generic-rest-target-adapter.md`](docs/generic-rest-target-adapter.md) içindedir.

### BYOM analizi

Deterministik analiz adayları daraltır → redactor secret/PII temizler → açıkça seçilmiş provider/model/endpoint’e minimum excerpt gönderilir → strict schema validation → sonuç `llm_assisted` olarak kaydedilir → provider/model/privacy provenance rapora eklenir. Hata durumunda deterministik bulgular korunur ve LLM check “failed/skipped” görünür.

## Güvenlik sınırları

- Filesystem root, OpenWebUI endpoint, parser subprocess, decoded payload, remote model, HTML report ve browser ayrı trust boundary’dir.
- Dosya boyutu/sayısı, PDF/DOCX object/page, decode depth/output, regex zamanı ve model response boyutu sınırlıdır.
- Şüpheli komut/payload hiçbir zaman çalıştırılmaz; URL varsayılan olarak fetch edilmez.
- Secret’lar DB’de plaintext tutulmaz; environment/file reference kullanılır ve log/UI’dan redakte edilir.
- HTML/Markdown/model output escape edilir; source HTML doğrudan render edilmez.
- Remote model varsayılan kapalıdır; endpoint görünür, explicit consent zorunlu ve audit/provenance kaydı vardır.
- Active Scan varsayılan `safe` profildir ve hedef sahibinin açık yetki beyanı olmadan çalışmaz. Destructive veya side-effect-capable payload hiçbir zaman varsayılan etkin değildir.
- Tool-use testleri yalnız canary/no-op/non-destructive action kullanır. Gerçek email, dosya, shell, database veya external API mutation’ı safe profilde yasaktır.
- Target response rapora doğrudan HTML olarak yazılmaz; secret/PII redaksiyonu ve boyut sınırı uygulanır.
- Local dashboard auth içermez; default bind `127.0.0.1` olur. Dış erişim korumasız desteklenmez.

## Hata davranışı

- Bir dosya parse edilemezse bütün scan çökmez; dosya `skipped/failed` nedeni ile raporlanır.
- Parser timeout/crash worker’ı kalıcı olarak bozmaz; job partial coverage ile devam edebilir.
- DB lock için bounded retry/busy timeout uygulanır; süre aşılırsa job güvenli şekilde failed olur.
- Worker restart sonrası lease süresi dolan job yeniden alınır; idempotent adımlar duplicate finding üretmez.
- Cancel isteği cooperative checkpoint’lerde uygulanır; scan `cancelled`, tamamlanan coverage korunur.
- OpenWebUI/model erişilemezse retry policy sonrası ilgili check/connector failed olur; eski veriler yeni scan gibi sunulmaz.
- Rule/model çıktısı schema dışıysa reddedilir; güvenlik açığı olarak işaretlenmez.
- Partial scan skorları coverage ile gösterilir ve eksik kategori “healthy” sayılmaz.
