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
| İngilizce yönlendirmeli başlangıç | Yalın `ragscanner` komutuyla mevcut |
| OCR ve anlamsal kopya analizi | Henüz mevcut değil |
| Kalıcılık, API, dashboard, geçmiş ve scheduler | Henüz mevcut değil |
| OpenWebUI ve vector store içerik connector’ları | Henüz mevcut değil |
| ModelProvider/BYOM entegrasyonu | Henüz mevcut değil |
| Aktif endpoint tarama CLI’ı | Mevcut değil; yalnızca core sözleşmeleri var |

`ragscanner scan`, yerel keşif → ayrıştırma → normalizasyon → chunking → statik güvenlik → kopya
analizi → chunk kalitesi → puanlama → raporlama işlem hattını çalıştırır.

## Kullanıcılar için hızlı başlangıç

Gereksinimler: Python 3.12 veya 3.13 ve [`uv`](https://docs.astral.sh/uv/).

Alfa sürümünü doğrudan GitHub’dan kurun:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Yalın komut İngilizce bir başlangıç akışı açar. Hangi kaynağı kullandığınızı sorar, sınırlandırılmış
yakındaki yerel kaynakları önerir ve tarama başlatabilir. OpenWebUI keşfi, yalnızca açık onaydan sonra
sabit loopback sağlık endpoint’lerini kontrol eder; henüz OpenWebUI içeriğini almaz.

Kurulumu tek bir RAGScanner komutuyla yönetin veya kaldırın:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

`uninstall` onay ister. Otomasyonlar `ragscanner uninstall --yes` kullanabilir. Bu komutlar kabuk
açmadan resmi `uv tool` ortamına yönlenir; `repair`, özgün kurulum kaynağını ve ayarları koruyarak tam
yeniden kurulum yapar.

PyPI sürümünden sonra kurulum `uv tool install ragscanner` komutunu kullanacaktır. Henüz PyPI paketi
veya sürüm etiketi yayımlanmamıştır.

## Doğrudan taramalar

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

RAGScanner, mevcut bir çıktı dosyasının üzerine varsayılan olarak yazmaz.

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
kalacaktır. OpenWebUI planlanan entegrasyonlardan biridir; ürünün çekirdeği değildir.

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

1. PDF/yol dayanıklılığı, kurulum, rapor ve terminal UX
2. SQLite tarama geçmişi ve kalıcılık
3. Uygulama API’ı ve tarama karşılaştırması
4. OpenWebUI kaynak connector’ı
5. Yerel dashboard ve scheduler
6. Ek kaynak connector’ları, target adapter’ları ve isteğe bağlı model sağlayıcıları
7. Paketleme ve dağıtım sağlamlaştırması

Planlanan özellikler hiçbir zaman mevcutmuş gibi sunulmaz. Ayrıntılar için
[ROADMAP.md](ROADMAP.md) belgesine bakın.

## Katkı ve lisans

Katkıda bulunmadan önce [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) ve
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) belgelerini okuyun. Secret’ları, exploit’leri veya müşteri
içeriğini herkese açık issue’larda yayımlamayın.

RAGScanner [Apache License 2.0](LICENSE) kapsamında lisanslanır. Tek bir ücretsiz, açık kaynaklı ürün
vardır: Community/Pro ayrımı, ücretli kural akışı, abonelik, yetkilendirme veya kapalı modül yoktur.
