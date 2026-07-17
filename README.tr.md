# RAGScanner

> Kullanıcılarınızdan önce RAG sisteminizi tarayın.

[English](README.md) · **Türkçe** · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner, RAG bilgi kaynaklarındaki güvenlik ve içerik kalitesi risklerini incelemek için ücretsiz,
açık kaynaklı ve önce yerel çalışan bir araçtır. Mevcut teknik alfa; TXT, Markdown, metin tabanlı PDF
ve DOCX dosyalarını tarar, ardından terminal, JSON veya bağımsız HTML raporları üretir.

Mevcut statik işlem hattı belgeleri uzak servislere göndermez, LLM gerektirmez, telemetri
çalıştırmaz, bağlantıları takip etmez ve tespit edilen komutları hiçbir zaman yürütmez.

> [!WARNING]
> Bu sürüm teknik alfadır. Statik tarama, çalışan bir RAG uygulamasının güvenli olduğunu kanıtlamaz
> ve prompt injection saldırılarına karşı eksiksiz koruma sağlamaz. Bulgular inceleme girdileridir;
> güvenlik garantisi değildir.

## Bugün çalışan özellikler

| Yetenek | Alfa durumu |
|---|---|
| Tek yerel dosya ve klasör taramaları | Mevcut |
| TXT, Markdown, metin tabanlı PDF ve DOCX | Mevcut |
| Deterministik normalizasyon ve kaynak eşleme | Mevcut |
| Yapı, paragraf ve token penceresi chunking | Mevcut |
| Sürümlendirilmiş statik RAG güvenlik kuralları | Mevcut |
| Tam ve sözcüksel yakın kopya analizi | Mevcut |
| Chunk kalite kontrolleri | Mevcut |
| Terminal, JSON ve bağımsız HTML raporları | Mevcut |
| Çevrimdışı statik tarama | Varsayılan davranış |
| Birleşik makine kurulumu ve dashboard açılışı | `ragscanner install`; yalın `ragscanner` dashboardu açar |
| İzinli container OpenWebUI keşfi ve KB/dosya metadata envanteri | Mevcut |
| OCR ve anlamsal kopya analizi | Henüz mevcut değil |
| İsteğe bağlı SQLite geçmişi ve kapsam duyarlı karşılaştırma | CLI üzerinden mevcut |
| Localhost geçmiş API’si | `ragscanner serve` ile mevcut |
| Dayanıklı SQLite statik tarama işleri ve worker | Mevcut |
| Kapsam yetkili kimlik doğrulamalı asenkron tarama/iş API’si | Loopback üzerinde mevcut |
| Yerel genel bakış ve kuyruk dashboard’u | `ragscanner serve` ile mevcut |
| Tarih/kaynak filtreli dashboard rapor arşivi, ayrıntı ve karşılaştırma | Mevcut |
| Gizli bilgi içermeyen kalıcı kaynak profilleri ve Sources/Settings yönetimi | Mevcut |
| Kullanıcı başına Yerel Agent | Kullanımdan kaldırıldı; yerini makine servisi aldı |
| Yerel yönetici ilk kurulumu olan makine-geneli Host Service | Mevcut |
| Docker, Podman, nerdctl, Finch, Kubernetes ve localhost metadata keşfi | Mevcut |
| Açık onaylı OpenWebUI bilgi tabanı içerik connector’ı | Mevcut |
| Scheduler ve vector store içerik connector’ları | Henüz mevcut değil |
| Tarama başına yerel/uzak AI destekli rapor analizi | Mevcut ve varsayılan olarak kapalı |
| Aktif endpoint tarama CLI’ı | Mevcut değil; yalnızca core sözleşmeleri var |

`ragscanner scan`, yerel keşif → ayrıştırma → normalizasyon → chunking → statik güvenlik → kopya
analizi → chunk kalitesi → puanlama → raporlama işlem hattını çalıştırır.

## Kullanıcılar için hızlı başlangıç

Gereksinimler: Python 3.12 veya 3.13 ve [`uv`](https://docs.astral.sh/uv/).

Alfa sürümünü doğrudan GitHub’dan kurun:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

`ragscanner install` makine servisini, yalıtılmış çalışma ortamını ve yerel dashboard adresini tek
seferde kurar ve varsayılan olarak dashboardu açar. Kurulumu CLI içinde tamamlamak için
`ragscanner install --mode terminal` kullanılabilir. Sonraki yalın `ragscanner` çalıştırmaları her
zaman dashboardu açar. Otomatik keşif yalnızca RAG odaklı ada sahip doğrudan klasörleri önerir; Documents gibi
genel klasörleri RAG kaynağı saymaz. OpenWebUI keşfi açık onaydan sonra mevcut
Docker, Podman, nerdctl veya Finch runtime’larından sınırlı metadata ile yaygın loopback adreslerini
inceler. Ayrı olarak sağlanan ve yalnız bellekte tutulan API anahtarı, erişilebilir knowledge base’ler
ile bunlara bağlı veya bağımsız/sohbet dosyalarının metadata envanterini çıkarabilir. 2. seçenek,
kullanıcının listelenen tek bir OpenWebUI bilgi tabanını seçmesine ve ayrı açık içerik onayından sonra
statik işlem hattını aynı yerel süreçte çalıştırmasına izin verir.

Kurulumu tek bir RAGScanner komutuyla yönetin veya kaldırın:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner status
ragscanner open
```

Bu komutlar yönetici izni gerektirir. `update` ve `repair` makine runtime'ını değiştirip Host Service'i
yeniden başlatır. Otomasyon `ragscanner uninstall --yes` kullanabilir. `uninstall`, `--purge-data`
verilmedikçe makine raporlarını ve geçmişini korur.

Kurulum ve onarım, `%ProgramFiles%\RAGScanner\command` dizinini Windows makine `PATH` değişkenine
kaydeder. Sabit `ragscanner.cmd` yönlendiricisi etkin runtime neslini izlediği için yeni terminaller,
kullanıcı profilindeki eski `uv` aracını değil makine kurulumunu kullanır. Güncellenmiş makine `PATH`
değerinin alınması için ilk kurulum veya onarımdan sonra terminalleri yeniden açın.
Makine yönlendiricisinden önce oluşturulan kurulumlarda, yönetici terminalinden tek geçiş gerekebilir:
`uvx --refresh --from git+https://github.com/atakaneser/RAGScanner.git@main ragscanner repair`.
Bu komut kullanıcı profiline başka bir araç kurmadan güncel onarım kodunu çalıştırır ve tekrarlanmaz.

PyPI sürümünden sonra kurulum `uv tool install ragscanner` komutunu kullanacaktır. Henüz PyPI paketi
veya sürüm etiketi yayımlanmamıştır.

## Doğrudan taramalar

AI destekli analiz her doğrudan tarama veya dashboard işi için ayrı seçilebilir. Yerel sağlayıcılar
Ollama, LM Studio, LocalAI ve vLLM'dir. Uzak seçenekler OpenRouter, OpenAI, NVIDIA NIM, Anthropic,
Google Gemini, Groq, Mistral AI, Together AI ve özel OpenAI uyumlu uç noktaları kapsar. AI varsayılan
olarak kapalıdır; uzak kullanım tarama başına açık onay gerektirir. Yalnızca sınırlandırılmış ve
maskelenmiş rapor özeti gönderilir; ham belgeler ve bulgu kanıtları gönderilmez. Sağlayıcı hatası
deterministik raporu geçersiz kılmaz.

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
```

Boşluk, parantez veya kabuk açısından hassas başka karakterler içeren yolları tırnak içine alın.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Rapor oluşturun:

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Yerel tarama geçmişini yalnızca istendiğinde kaydedin ve karşılaştırın:

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

Dayanıklı taramaları kuyruğa alın ve worker’ı çalıştırın:

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

Açık onaylı OpenWebUI taraması için kimlik bilgisini SQLite dışında tutun:

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` yerel dashboard’u açar. API üzerinden kapsam yetkili Bearer kimlik doğrulamalı
tarama oluşturma ve iş kontrolünü etkinleştirmek için `RAGSCANNER_API_KEY` ayarlayın. Sunucu yalnızca
`127.0.0.1` adresine bağlanır.

RAGScanner, mevcut bir çıktı dosyasının üzerine varsayılan olarak yazmaz.

## Tam CLI komut referansı

Kurulu sürümün kesin söz dizimi için `ragscanner COMMAND --help` çalıştırın. Aşağıdakiler herkese açık
arayüzün tamamıdır; dahili uyumluluk komutları bilerek gizlenmiştir.

### Çalıştırma ve tanılama

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner` | RAGScanner kuruluysa dashboard'u açar; değilse kurulum komutunu gösterir. |
| `ragscanner --version` | Kurulu CLI sürümünü gösterir. |
| `ragscanner --help` / `ragscanner COMMAND --help` | Makine durumunu değiştirmeden genel yardımı veya komuta özgü seçenekleri gösterir. |
| `ragscanner --install-completion` / `--show-completion` | Typer'ın desteklediği kabuk tamamlamasını kurar veya tamamlama betiğini gösterir. |
| `ragscanner doctor` | Kurulum, yollar, yapılandırma, ayrıştırıcılar ve çalışma zamanı için çevrimdışı tanılama yapar. |
| `ragscanner paths` | Geçerli işletim sistemindeki makine yapılandırması, veri, rapor, geçici ve eski yol konumlarını gösterir. |

### Makine kurulumu ve yaşam döngüsü

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner install` | Yalıtılmış makine çalışma zamanını ve Host yöneticisini (Windows `SYSTEM` başlangıç görevi, Linux systemd veya macOS LaunchDaemon) kurar, `local.ragscanner.com` adresini yapılandırır, makine verisini başlatır ve dashboard'u açar. Gerektiğinde yönetici yükseltmesi ister. |
| `ragscanner install --yes` | Katılımsız kurulum için olağan istemleri kabul eder; işletim sistemi yükseltmesi yine gerekebilir. |
| `ragscanner install --mode terminal` | Varsayılan dashboard kurulumu yerine terminal kurulumunu tamamlar. Geçerli modlar `dashboard` ve `terminal` değerleridir. |
| `ragscanner install --no-open-dashboard` | Her şeyi kurar ancak tamamlanınca tarayıcı açmaz. |
| `ragscanner open` | Kurulu dashboard'u varsayılan tarayıcıda açar. İkinci bir ön plan sunucusu başlatmaz. |
| `ragscanner status` | Makine kurulumu, servis, dashboard, çalışma zamanı ve veri yolu durumunu gösterir. |
| `ragscanner update` | Resmî GitHub deposundaki en güncel `main` dalını indirir, yalıtılmış makine çalışma zamanına kurar ve servisi yeni sürüme geçirir; yönetici izni gerekir. Ayrı bir `uv tool install` komutu gerekmez. |
| `ragscanner repair` | En güncel `main` dalını indirip yeniden kurar; ardından çalışma zamanı, servis, ana bilgisayar adı, dizinler ve yapılandırmayı düzeltir; yönetici izni gerekir. Ayrı bir `uv tool install` komutu gerekmez. |
| `ragscanner uninstall` | Onaydan sonra servis, çalışma zamanı ve ana bilgisayar adı eşlemesini kaldırır; raporları ve geçmişi korur. |
| `ragscanner uninstall --yes --purge-data` | Etkileşimsiz kaldırma yapar ve makine yapılandırmasını, rapor geçmişini ve yönetilen veriyi de siler. Bu işlem geri alınamaz. |

### Doğrudan yerel taramalar

```text
ragscanner scan PATH [OPTIONS]
```

`PATH`, desteklenen bir dosya veya dizin olabilir. Boşluk ya da kabuğa özel karakter içeren yolları
tırnak içine alın. Doğrudan taramalar yerelde çalışır; açıkça seçilmedikçe AI zenginleştirmesi kapalıdır.

| Seçenek | Ayrıntılı kullanım |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | Terminal çıktısını veya açık bir JSON/HTML dışa aktarımını seçer. Dosya dışa aktarımları çıktı yolu ister ve mevcut dosyanın üzerine yazmaz. |
| `--include GLOB`, `--exclude GLOB` | Dizin keşfini dahil etme/dışlama glob desenleriyle daraltır. Seçenekler tekrarlanabilir. |
| `--recursive` / `--no-recursive` | Alt dizinlere inmeyi açar veya kapatır; özyineleme varsayılan olarak açıktır. |
| `--max-file-size BYTES`, `--max-files COUNT` | Keşfedilen girdi boyutuna ve dosya sayısına pozitif güvenlik sınırları uygular. |
| `--category NAME`, `--exclude-rule ID` | Seçilen kural kategorilerini dahil eder veya kural kimliklerini çıkarır; birden çok değer için tekrarlayın. |
| `--include-pii` / `--no-include-pii` | Etkin tarama politikasındaki PII odaklı kuralları açar veya kapatır. |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | Gösterilen bulguları filtreler, sıfır olmayan çıkış üreten önem düzeyini seçer ve rapor hacmini sınırlar. |
| `--config FILE` | Yalnızca varsayılanlar ve makine yapılandırması yerine açık bir yapılandırma dosyasından tarama politikası yükler. |
| `--security-only`, `--quality-only` | Yalnızca güvenlik veya yalnızca kalite ailesini çalıştırır. İki anahtarı birlikte kullanmayın. |
| `--quiet`, `--verbose`, `--no-color` | Tarama sonucunu değiştirmeden terminal ayrıntısını ve ANSI rengini denetler. |
| `--save-history`, `--history-db FILE` | Sürümlü rapor anlık görüntüsünü saklar ve isteğe bağlı olarak varsayılan olmayan SQLite geçmiş veritabanını seçer. |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | Seçilen sağlayıcı/model ve isteğe bağlı uyumlu uç noktayla rapor zenginleştirmesini açar. |
| `--ai-credential-ref REF`, `--consent-remote-ai` | `env:OPENROUTER_API_KEY` gibi harici bir kimlik bilgisi çözümler ve uzak sağlayıcı için gerekli onayı kaydeder. |

### AI rapor zenginleştirmesi

| Komut veya seçenek | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | Desteklenen mevcut bir raporu zenginleştirip yeni bir rapor yazar; model ve çıktı zorunludur. |
| `--provider NAME` | Analiz sağlayıcısını seçer; varsayılan `ollama`dır. Yapılandırılmış seçenekler yerel ve uzak OpenAI uyumlu sağlayıcıları kapsar. |
| `--base-url URL`, `--credential-ref REF` | Sağlayıcı uç noktasını geçersiz kılar ve sırrı rapor/geçmiş içeriği dışında çözümler. |
| `--consent-remote` | Sınırlı ve maskelenmiş rapor özetinin uzak analiz sağlayıcısına gönderilmesine açıkça izin verir. Ham belgeler ve kanıtlar gönderilmez. |

### Kalıcı işler ve worker

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | Kalıcı yerel dosya/klasör taraması kuyruğa alır. `--database`, `--config`, `--idempotency-key`, `--max-attempts` ve doğrudan tarama AI seçeneklerini kabul eder. |
| `ragscanner jobs enqueue-openwebui` | OpenWebUI bilgi taraması kuyruğa alır. `--base-url`, `--knowledge-id`, `--credential-ref` ve `--consent-content` zorunludur; veritabanı, tekilleştirme, yeniden deneme ve AI seçeneklerini de kabul eder. |
| `ragscanner jobs list` | `--database`, `--limit` (1–200), `--offset` ve `--format` ile kuyruktaki ve tamamlanan işleri listeler. |
| `ragscanner jobs show JOB_ID` | Bir işin denemelerini, zamanlarını, sonuç başvurusunu ve hata durumunu gösterir; `--database` depoyu seçer. |
| `ragscanner jobs cancel JOB_ID` | Son duruma ulaşmamış işi iptal eder; `--database` depoyu seçer. |
| `ragscanner jobs retry JOB_ID` | Uygun başarısız/iptal edilmiş iş için yeni çalıştırılabilir deneme oluşturur; `--database` depoyu seçer. |
| `ragscanner worker` | Makine iş veritabanındaki kalıcı işleri sürekli kiralar ve yürütür. |
| `ragscanner worker --once` | Mevcut işi bir kez işler ve çıkar; testler ve zamanlanmış çalıştırmalar için kullanışlıdır. |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | Depo, yoklama (0,1–60), kiralama (5–3600) ve kararlı worker kimliği denetimleridir. |

### Saklanan rapor geçmişi

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner history list` | Saklanan taramaları listeler. `--database`, `--limit` (1–200), `--offset` ve `--format` kabul eder. |
| `ragscanner history show SCAN_ID` | Bir saklanan raporu `--database`, `--format` ve isteğe bağlı ayrıntılı kanıt için `--verbose` ile oluşturur. |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | İki yürütmeyi karşılaştırıp yeni, çözülen ve değişmeyen bulguları raporlar; `--database` ve `--format` kabul eder. |
| `ragscanner history delete SCAN_ID` | Onaydan sonra bir saklanan raporu siler. `--yes` yalnızca bilinçli otomasyonda kullanılmalıdır; `--database` depoyu seçer. |

### Oluşturma ve ön plan servisi

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner report SCAN_RESULT` | Bir tarama sonucu dosyasını `--format`, `--output`, `--verbose`, önem/kategori/sınıflandırma/kural/belge/hedef filtreleri, `--max-findings`, `--include-info` veya `--exclude-info` ve isteğe bağlı `--show-absolute-paths` ile yeniden oluşturur. |
| `ragscanner serve` | Dashboard/API'yi geliştirme veya tanılama için loopback üzerinde ön planda çalıştırır; normal kurulu kullanım makine servisine dayanır. |
| `ragscanner serve --port PORT --history-db FILE` | Loopback portunu (1–65535) ve alternatif rapor geçmişi veritabanını seçer. |

### Özelleşmiş tarayıcılar

| Komut | Ayrıntılı kullanım |
| --- | --- |
| `ragscanner security scan PATH` | Yalnızca güvenlik kurallarını çalıştırır. Kural/kategori/önem filtreleri, `--format`, `--fail-on`, `--max-findings`, `--include-pii` ve `--offline` veya `--no-offline` destekler; varsayılan çevrimdışıdır. |
| `ragscanner quality scan PATH` | Bağımsız tam kopya, yakın kopya ve parça kalitesi anahtarlarının yanında `--similarity-threshold` (0,5–1,0), parça token sınırları, `--fail-on` ve `--format` ile kalite kontrolleri yapar. |

### İşletim kuralları

| Kural | Anlamı |
| --- | --- |
| Çıkış durumu | Geçersiz girdi, işletim hatası veya `--fail-on` düzeyindeki/üzerindeki bulgu CI için uygun sıfır olmayan çıkış üretir. |
| Onay | OpenWebUI belge erişimi ve uzak AI kullanımı açık onay anahtarlarını gerektirir; yalnızca metadata keşfi içerik erişimi sağlamaz. |
| Kimlik bilgileri | Sırları ortam değişkenlerinde veya desteklenen harici çözücüde saklayın; yalnızca kimlik bilgisi başvurusunu geçirin. |
| Depolama | Belirtilmeyen veritabanı/çıktı yolları `ragscanner paths` tarafından gösterilen işletim sistemine özgü makine konumlarına çözümlenir. |
| Servisler | Kurulu dashboard/worker makine kapsamındadır; geçici ön plan `serve` ve `worker` komutları tanılama için kullanılabilir. |
| Çıktı güvenliği | Mevcut dışa aktarım dosyalarının üzerine yazılmaz, mutlak kaynak yolları varsayılan olarak gizlenir ve rapor kanıtı sınırlanıp kaçışlanır. |
| Uyumluluk | Seçenek adları ve komut çıktıları İngilizcedir; taranan RAG içeriği desteklenen her dilde Unicode tabanlı kalır. |

## Çok dilli girdi

Ürünün ürettiği arayüz etiketleri, durum metinleri, hata mesajları, düzeltme önerileri, metadata ve
kanonik belgeler İngilizcedir. RAG kaynakları Unicode uyumluluğunu korur ve Türkçe, Almanca,
Fransızca, Çince, İtalyanca, Arapça, Kiril, CJK, emoji ve NFC/NFD dosya adı çeşitlerini içerebilir.

Denetim doğruluğunu korumak için kaynaktan türetilen kanıt özgün dilinde tutulur. Yerelleştirilmiş
README dosyaları, İngilizce olmayan kasıtlı proje belgelerinin tamamıdır.

## Raporları anlama

Raporlar şunları birbirinden ayırır:

- tarama tamamlanma durumu ve kısmi kapsam;
- önem derecesi ve güven düzeyi;
- `confirmed`, `probable`, `ambiguous` ve `not_detected` sınıflandırmaları;
- değerlendirilen, kısmi, başarısız ve `not_assessed` kontroller;
- mevcut olduğunda belge, sayfa, chunk ve kaynak konumları;
- tarayıcı, kural paketi ve politika sürümleri.

`not_assessed`, sağlıklı veya sıfır risk anlamına gelmez. Güvenlik puanı, güvenlik garantisi değildir.
Statik tarama ve yetkilendirilmiş aktif endpoint testi ayrı modlardır.

## Gizlilik ve güvenlik modeli

- Statik taramalar yereldir ve gizli ağ çağrıları yapmaz.
- Belge veya chunk içeriği harici AI servislerine gönderilmez.
- URL’ler ayrıştırılabilir ancak getirilmez.
- Şüpheli payload’lar, makrolar, kabuk komutları ve gömülü nesneler yürütülmez.
- DOCX harici ilişkileri takip edilmez; PDF ekleri çıkarılmaz.
- Kanıt sınırlandırılır, HTML açısından escape edilir ve secret benzeri desenler maskelenir.
- Mutlak kaynak yolları raporlarda varsayılan olarak gizlenir.
- Telemetri, faturalandırma, abonelik, yetkilendirme veya lisans sunucusu yoktur.

Uzak connector’lar ve isteğe bağlı modeller, açıkça yapılandırılıp onaylanana kadar devre dışı
kalır. OpenWebUI içerik erişimi seçilmiş bir bilgi tabanı, harici kimlik bilgisi referansı ve açık
onay gerektirir; ürünün çekirdeği değil, entegrasyonlardan biridir.

## Katkıda bulunanlar için kurulum

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

Kalite kontrolleri:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

Tüm fixture’lar sentetik olmalıdır. Gerçek kimlik bilgilerini, müşteri belgelerini veya kişisel
verileri hiçbir zaman eklemeyin.

## Mimari

Core; UI framework’lerinden, veritabanlarından, connector’lardan, model sağlayıcılarından ve MCP’den
bağımsız kalır. Entegrasyon rolleri bilinçli olarak ayrılmıştır:

- `SourceConnector` belgeleri, chunk’ları, metadata’yı veya bilgi tabanı içeriğini okur.
- `TargetAdapter`, çalışan bir RAG/chat uygulamasına yetkilendirilmiş black-box testleri gönderir.
- `ModelProvider`, RAGScanner’ın kendisi için isteğe bağlı bir analiz modeli sağlar.

OpenAI, Hugging Face veya OpenWebUI kullanılması retrieval bulunduğunu kanıtlamaz. Bir hedef yalnızca
belge/vector/index retrieval doğrulandığında RAG hedefi olarak adlandırılır.

Ayrıntılı sınırlar ve güncel durum için [ARCHITECTURE.md](ARCHITECTURE.md),
[PRODUCT.md](PRODUCT.md) ve [docs/status/current.md](docs/status/current.md) belgelerine bakın.

## Yol haritası

Yakın dönem sıralaması şöyledir:

1. Kalan kalıcılık kurtarma ve API ölçeğinde geçmiş/karşılaştırma işleri
2. Yetenek katmanlı SharePoint, web, SaaS, Git, object store ve vector connector’ları
3. OpenWebUI uyumluluğu, artımlı değişiklik algılama, kaynak kimliği ve secret sağlayıcıları
4. Zamanlama, saklama politikası, yinelenen işler ve rapor arayüzü yerelleştirmesi
5. Scheduler, saklama ve bildirimler
6. Paketleme ve dağıtım sağlamlaştırması

Planlanan özellikler hiçbir zaman mevcutmuş gibi sunulmaz. Ayrıntılar için
[ROADMAP.md](ROADMAP.md) belgesine bakın.

## Katkı ve lisans

Katkıda bulunmadan önce [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) ve
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) belgelerini okuyun. Secret’ları, exploit’leri veya müşteri
içeriğini herkese açık issue’larda yayımlamayın.

RAGScanner [Apache License 2.0](LICENSE) kapsamında lisanslanır. Tek bir ücretsiz, açık kaynaklı ürün
vardır: Community/Pro ayrımı, ücretli kural akışı, abonelik, yetkilendirme veya kapalı modül yoktur.
