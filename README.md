# RAGScanner

> Scan your RAG before your users do.

RAGScanner, RAG bilgi kaynaklarındaki güvenlik ve içerik kalitesi risklerini yerel olarak inceleyen,
tamamen ücretsiz ve açık kaynaklı bir araçtır. İlk alpha sürümü TXT, Markdown, metin tabanlı PDF ve
DOCX kaynaklarını tek dosya veya klasör olarak işler; normalize eder, chunk'lara ayırır, deterministik
güvenlik kurallarını ve yerel kalite kontrollerini çalıştırır, ardından terminal, JSON veya bağımsız
HTML raporu üretir.

RAGScanner mevcut alpha kapsamında belge içeriğini dış servislere göndermez, LLM gerektirmez,
telemetry çalıştırmaz, bağlantıları takip etmez ve tespit ettiği komutları yürütmez.

> [!WARNING]
> Bu sürüm teknik alpha'dır. Static tarama, çalışan bir RAG uygulamasının saldırıya açık olduğunu
> tek başına kanıtlamaz ve eksiksiz prompt-injection koruması sağlamaz. Bulgular inceleme girdisidir.

## İçindekiler

- [Neler çalışıyor?](#neler-çalışıyor)
- [Hızlı başlangıç](#hızlı-başlangıç)
- [Kurulum](#kurulum)
- [İlk tarama](#ilk-tarama)
- [Raporları yorumlama](#raporları-yorumlama)
- [Static güvenlik taraması](#static-güvenlik-taraması)
- [Tek ve çok kaynaklı knowledge base](#tek-ve-çok-kaynaklı-knowledge-base)
- [Yapılandırma](#yapılandırma)
- [Gizlilik ve güvenlik modeli](#gizlilik-ve-güvenlik-modeli)
- [Mimari](#mimari)
- [Geliştirme](#geliştirme)
- [Sorun giderme](#sorun-giderme)
- [Yol haritası](#yol-haritası)
- [Katkı ve lisans](#katkı-ve-lisans)

## Neler çalışıyor?

| Yetenek | Alpha durumu |
|---|---|
| Tek dosya ve yerel klasör tarama | Kullanılabilir |
| TXT, Markdown, metin tabanlı PDF ve DOCX | Kullanılabilir |
| Deterministik normalization ve source mapping | Kullanılabilir |
| Structure/paragraph/token-window chunking | Kullanılabilir |
| Static RAG güvenlik rule pack'i | Kullanılabilir |
| Exact ve lexical near-duplicate analizi | Kullanılabilir |
| Chunk-quality kontrolleri | Kullanılabilir |
| Terminal, JSON ve standalone HTML rapor | Kullanılabilir |
| Tamamen offline çalışma | Varsayılan ve mevcut unified scan davranışı |
| OCR ve semantic duplicate analizi | Henüz yok |
| Dashboard, API, history ve scheduler | Henüz yok |
| OpenWebUI ve vector-store connector'ları | Henüz yok |
| Model provider/BYOM entegrasyonu | Henüz yok |
| Active endpoint scan CLI | Henüz yok; yalnız core kontratları mevcut |

`ragscanner scan` kullanılabilir ana komuttur. Source discovery → parsing → normalization → chunking
→ static security → duplicate/near-duplicate → chunk quality → scoring → reporting akışını tek bir
yerel pipeline içinde çalıştırır.

## Hızlı başlangıç

Gereksinimler:

- Python 3.12 veya 3.13
- [`uv`](https://docs.astral.sh/uv/)
- Git

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

HTML rapor üretmek için:

```bash
uv run ragscanner scan ./examples/sample-kb \
  --format html \
  --output ragscanner-report.html
```

RAGScanner mevcut bir output dosyasının üzerine varsayılan olarak yazmaz. Aynı komutu yeniden
çalıştırmadan önce önceki dosyayı başka bir yere taşıyın veya farklı bir output yolu verin.

## Kurulum

### Kaynak koddan geliştirme kurulumu

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
```

Kurulumu doğrulayın:

```bash
uv run ragscanner --version
uv run ragscanner doctor
```

Beklenen alpha sürümü:

```text
RAGScanner 0.1.0a1
```

`doctor` yalnız yerel paket ve yapılandırma durumunu kontrol eder; ağ bağlantısı kurmaz.

### Wheel oluşturma

Paket henüz PyPI'da yayımlanmamıştır. Yerel wheel oluşturmak için:

```bash
uv build
```

Oluşan wheel `dist/` altındadır ve static rule dosyalarıyla JSON report schema'sını içerir.

## İlk tarama

### Bir klasörü tarama

```bash
uv run ragscanner scan ./knowledge-base
```

### Tek dosyayı tarama

```bash
uv run ragscanner scan ./knowledge-base/guide.md
uv run ragscanner scan ./knowledge-base/manual.pdf
uv run ragscanner scan ./knowledge-base/policy.docx
```

Tek dosya verildiğinde aynı dizindeki diğer dosyalar örtük olarak taranmaz.

### JSON rapor üretme

```bash
uv run ragscanner scan ./knowledge-base \
  --format json \
  --output report.json
```

JSON formatı `schemas/report/ragscanner-report-v1.schema.json` ile sürümlenir.

### Yalnız güvenlik veya kalite kontrolleri

```bash
uv run ragscanner scan ./knowledge-base --security-only
uv run ragscanner scan ./knowledge-base --quality-only
```

### CI'da bulgu eşiği kullanma

```bash
uv run ragscanner scan ./knowledge-base --fail-on high --format json --output report.json
```

`--fail-on`, belirtilen veya daha yüksek severity bulunduğunda uygun non-zero exit code üretir.
Taramanın teknik olarak tamamlanması ile policy eşiğinin aşılması birbirinden ayrıdır.

### Dosya seçimi ve limitler

```bash
uv run ragscanner scan ./knowledge-base \
  --include "**/*.md" \
  --exclude "**/archive/**" \
  --max-file-size 26214400 \
  --max-files 1000 \
  --max-findings 500
```

Tüm seçenekleri görmek için:

```bash
uv run ragscanner scan --help
uv run ragscanner security scan --help
uv run ragscanner quality scan --help
uv run ragscanner report --help
```

## Raporları yorumlama

Raporlar şu bilgileri açıkça ayırır:

- `status`: taramanın tamamlanıp tamamlanmadığı veya partial/skipped sonucu;
- severity: olası etkinin büyüklüğü;
- confidence: eşleşme kanıtının gücü;
- classification: `confirmed`, `probable`, `ambiguous` veya `not_detected`;
- assessment coverage: hangi kontrollerin değerlendirildiği veya neden `not_assessed` olduğu;
- source location: belge, page/line/chunk ve mümkün olduğunda normalize → original mapping;
- scanner/rule sürümü: sonucun hangi deterministik sürümle üretildiği.

`Not assessed`, başarılı veya sıfır risk anlamına gelmez. Örneğin retrieval doğruluğu, answer
reliability, cross-document freshness, version conflict ve tam RAG Rot değerlendirmeleri gerekli
scanner ya da koleksiyon bağlamı yoksa açıkça `not_assessed` gösterilir.

Rapor biçimleri:

- **Terminal:** hızlı yerel inceleme; ANSI zorunlu değildir.
- **JSON:** otomasyon ve schema doğrulaması için versioned çıktı.
- **HTML:** external JavaScript/asset içermeyen, untrusted evidence'ı escape eden bağımsız dosya.

Tamamen sentetik örnek çıktılar `examples/scan-results/` ve `examples/reports/` altındadır.

## Static güvenlik taraması

Static scanner; ham/normalize belge içeriğini, chunk'ları, metadata'yı, parser warning'lerini ve
normalization annotation'larını yerel rule pack ile inceler.

```bash
uv run ragscanner security scan ./knowledge-base --offline
uv run ragscanner security scan ./knowledge-base/file.pdf --format json
uv run ragscanner security scan ./knowledge-base --category prompt_injection
uv run ragscanner security scan ./knowledge-base --rules STATIC-PI-001
uv run ragscanner security scan ./knowledge-base --exclude-rule STATIC-PI-001
uv run ragscanner security scan ./knowledge-base --include-pii
```

İlk versioned rule pack şu alanları kapsar:

- İngilizce ve Türkçe prompt injection/instruction override;
- system prompt extraction girişimleri;
- tool/function abuse talimatları;
- AI/agent bağlamındaki şüpheli shell, PowerShell ve SQL komutları;
- bounded Base64, ROT13, Unicode escape ve hex incelemesi;
- zero-width, bidi, HTML comment ve hidden DOCX göstergeleri;
- API key, bearer token, private key ve connection string benzeri secret'lar;
- isteğe bağlı, muhafazakâr PII pattern'leri;
- metadata endpoint, credential URL ve risk bağlamındaki şüpheli URL'ler;
- title, author, keyword ve custom metadata içindeki poisoning talimatları.

PII taraması varsayılan kapalıdır. Pattern eşleşmesi bir kişinin kimliğini veya verinin gerçekten
hassas olduğunu kanıtlamaz. Secret evidence rapora girmeden maskelenir. Encoded içerik sınırlı
boyut/derinlikte yalnız inceleme için çözülür; çalıştırılmaz.

Rule formatı ve false-positive politikası için
[`docs/static-security-scanner.md`](docs/static-security-scanner.md) ve
[`docs/security-rules.md`](docs/security-rules.md) belgelerine bakın.

## Tek ve çok kaynaklı knowledge base

RAGScanner tek büyük dosyayı geçerli bir knowledge base olarak kabul eder. Tek kaynak olması hata
veya warning değildir; raporda `single_source` ve `source_count: 1` gösterilir.

Tek dosyada:

- parse, normalization, chunking, static security ve chunk-quality çalışır;
- aynı belge içindeki repeated chunk ve lexical near-duplicate içerikler aranır;
- belgeler arası duplicate, version conflict ve cross-document freshness `not_assessed` olur;
- rapor, koleksiyon karşılaştırmasının neden yapılmadığını açıklar.

İki, üç, dört veya daha fazla dosyada `collection` modu kullanılır. Cross-document exact ve lexical
near-duplicate kontrolleri çalışır. Henüz uygulanmamış version conflict/freshness scanner'ları kaynak
sayısından bağımsız biçimde `not_assessed` kalır.

Büyük dosyalarda dosya, PDF page, extracted/normalized character ve chunk limitleri uygulanır.
Limit aşımı tüm taramayı kontrolsüz biçimde çökertmek yerine typed skipped/partial/failed sonuç ve
açıklama üretir.

## Yapılandırma

Unified scan yalnız yerel TOML yapılandırması kabul eder. Bilinmeyen alanlar reddedilir; arbitrary
code, dynamic import, environment interpolation veya secret alanı yoktur. Öncelik sırası:

```text
varsayılanlar < TOML dosyası < açık CLI seçenekleri
```

Başlangıç örneği `examples/ragscanner.toml` dosyasındadır:

```bash
cp examples/ragscanner.toml ragscanner.toml
uv run ragscanner scan ./knowledge-base --config ragscanner.toml
```

Temel örnek:

```toml
[scan]
recursive = true
include = ["**/*.pdf", "**/*.docx", "**/*.md", "**/*.txt"]
exclude = ["**/archive/**"]
max_file_size_mb = 25
max_files = 10000

[security]
enabled = true
include_pii = false
minimum_severity = "low"

[chunking]
strategy = "structure_aware"
target_tokens = 500
max_tokens = 800
min_tokens = 50
overlap_tokens = 50

[duplicates]
exact = true
near = true
similarity_threshold = 0.88

[limits]
pdf_max_pages = 1000
pdf_max_characters = 5000000
docx_max_characters = 5000000
normalized_max_characters = 5000000
max_chunks_per_document = 10000

[report]
format = "html"
output = "ragscanner-report.html"
show_relative_paths = true
max_findings = 500
overwrite = false
```

Ayrıntılı alan açıklamaları için [`docs/configuration.md`](docs/configuration.md) belgesine bakın.

## Gizlilik ve güvenlik modeli

- Unified static scan tamamen yereldir ve gizli network çağrısı yapmaz.
- Belge veya chunk içeriği harici AI/model servisine gönderilmez.
- URL'ler parse edilebilir fakat fetch edilmez.
- Şüpheli payload, macro, shell/SQL komutu veya embedded object çalıştırılmaz.
- DOCX dış ilişkileri takip edilmez; PDF attachment çıkarılmaz; Markdown/HTML render edilmez.
- Evidence bounded, HTML-escaped ve secret pattern'lerinde maskelidir.
- Absolute source path raporda varsayılan olarak gizlenir.
- Telemetry, analytics, billing, abonelik ve lisans sunucusu yoktur.

Active black-box scan farklı bir scan modudur ve yalnız hedef sahibinin açık yetkisiyle çalışmalıdır.
Bir LLM endpoint'i retrieval yaptığı doğrulanmadan RAG target sayılmaz. OpenAI, Hugging Face veya
OpenWebUI kullanılması tek başına retrieval bulunduğunu kanıtlamaz. OpenWebUI planlanan
entegrasyonlardan biridir; ürünün core runtime'ı değildir.

Güvenlik sınırları ve bildirim süreci için [`SECURITY.md`](SECURITY.md) belgesini okuyun. Secret,
exploit veya müşteri içeriğini public issue olarak paylaşmayın.

## Mimari

Core; UI, database, connector, model sağlayıcısı ve platform vendor'larından bağımsızdır.

```text
CLI / gelecekte API ve dashboard
              |
      application pipeline
              |
  parser -> normalizer -> chunker
              |
 security + duplicates + quality
              |
     terminal / JSON / HTML
```

Entegrasyon rolleri bilinçli olarak ayrıdır:

- **SourceConnector:** belge, chunk ve knowledge-base içeriğini okur.
- **TargetAdapter:** yetkili çalışan uygulamaya güvenli active test istekleri gönderir.
- **ModelProvider:** RAGScanner'ın opsiyonel ileri analiz modeli olur.

Aynı platform bu rollerin birden fazlasını sunabilse de configuration, credential, consent ve
provenance ayrı tutulur. Ayrıntılar için [`ARCHITECTURE.md`](ARCHITECTURE.md) ve
[`docs/decisions/`](docs/decisions/) dizinine bakın.

## Geliştirme

Yerel kalite kapıları:

```bash
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
```

Belirli bir testi çalıştırmak için:

```bash
uv run pytest tests/integration/test_static_scan_pipeline.py -v
```

Test fixture'ları sentetiktir; gerçek credential, müşteri belgesi veya kişisel veri eklemeyin.
Her uygulama değişikliği test ve güncel dokümantasyon içermelidir. Katkı akışı için
[`CONTRIBUTING.md`](CONTRIBUTING.md), test stratejisi için [`TESTING.md`](TESTING.md) belgelerine
bakın.

Repository yerleşimi:

```text
apps/                   # gelecekte API, web ve worker composition roots
packages/scanner/       # mevcut Python core, CLI ve local adapter'lar
packages/connectors/    # gelecekte source adapter'ları
packages/targets/       # gelecekte active target adapter'ları
packages/providers/     # gelecekte optional model provider adapter'ları
rules/static/           # versioned declarative static security rules
schemas/report/         # versioned report schema
tests/                  # unit, contract ve integration testleri
examples/               # sentetik knowledge base, config ve rapor örnekleri
docs/                   # ürün, mimari, kontrat ve durum belgeleri
```

## Sorun giderme

### `uv` bulunamıyor

[`uv` kurulum rehberini](https://docs.astral.sh/uv/getting-started/installation/) izleyin, ardından
`uv --version` ile doğrulayın.

### PDF'de içerik bulunmuyor

Alpha parser yalnız text-based PDF işler. Tarama `scanned/image-only` warning'i veriyorsa OCR henüz
uygulanmadığı için görüntü içindeki metin değerlendirilemez.

### Rapor dosyası zaten var

Output overwrite varsayılan kapalıdır. Farklı bir `--output` yolu verin veya mevcut raporu güvenli
biçimde başka yere taşıyın.

### Bazı kontroller `Not assessed`

Bu bir hata değildir. Raporun assessment coverage bölümünde eksik koleksiyon bağlamı veya henüz
uygulanmamış scanner gibi neden açıklanır.

### Static bulgu beklenmedik görünüyor

Documentation, quoted example ve güvenlik makalesi bağlamı confidence/classification değerini
düşürür; ancak belirsiz riskler tamamen gizlenmez. Evidence ve source location'ı inceleyin. False
positive/negative mümkündür.

### Tarama limit nedeniyle partial/skipped

`examples/ragscanner.toml` içindeki file/page/character/chunk limitlerini kaynak boyutunu ve makine
kapasitesini dikkate alarak ayarlayın. Limitleri kaldırmak yerine kontrollü artırın.

Daha fazla bilgi için [`SUPPORT.md`](SUPPORT.md) ve `docs/` altındaki bileşen belgelerine bakın.

## Yol haritası

Önerilen sonraki ürün adımı SQLite-first scan history/persistence katmanıdır. Sonraki aşamalarda API,
dashboard, scheduler/worker, OpenWebUI connector, diğer source/target adapter'ları, model provider,
OCR, semantic analiz ve daha kapsamlı health/RAG Rot değerlendirmeleri planlanmaktadır.

Planlanan özellikler mevcutmuş gibi sunulmaz. Güncel durum için
[`docs/status/current.md`](docs/status/current.md), sıralama için [`ROADMAP.md`](ROADMAP.md) ve
uyumluluk seviyeleri için [`COMPATIBILITY.md`](COMPATIBILITY.md) belgelerine bakın.

## Katkı ve lisans

RAGScanner tek ve ücretsiz üründür. Community/Pro ayrımı, ücretli rule feed'i, abonelik, entitlement
veya kapalı modül yoktur.

Katkılar memnuniyetle karşılanır. Başlamadan önce [`CONTRIBUTING.md`](CONTRIBUTING.md),
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) ve [`SECURITY.md`](SECURITY.md) belgelerini okuyun.

Bu proje [Apache License 2.0](LICENSE) altında lisanslanmıştır.
