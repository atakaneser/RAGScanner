# RAGScanner

> Kullanıcılarınızdan önce RAG sisteminizi tarayın.

[English](README.md) · **Türkçe** · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner; RAG bilgi kaynaklarındaki güvenlik ve içerik kalitesi riskleri için ücretsiz, açık
kaynaklı ve yerel öncelikli bir tarayıcıdır. Deterministik taramayı, kalıcı işleri, rapor geçmişini,
zamanlanmış izlemeyi ve isteğe bağlı AI yorumunu makine-yerel bir dashboard’da birleştirir.

> [!WARNING]
> RAGScanner teknik alpha aşamasındadır. Statik rapor bir inceleme yardımcısıdır; çalışan bir RAG
> sisteminin güvenli olduğunu veya tüm prompt-injection yöntemlerinden korunduğunu kanıtlamaz.

## Şu anda kullanılabilir

| Alan | Mevcut yetenek |
|---|---|
| Yerel içerik | Tek dosyalar ve kökle sınırlandırılmış klasörler |
| Formatlar | Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB, RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML ve loglar |
| Uzak kaynaklar | OpenWebUI bilgi tabanları; HTTPS sayfaları, belgeler, aynı kaynaklı sitemap’ler ve erişilebilir SharePoint URL’leri |
| Analiz | Statik güvenlik kuralları, tam/sözcüksel kopya ve chunk kalitesi kontrolleri |
| Raporlar | Terminal/JSON ile yerelleştirilmiş bağımsız HTML, Excel ve PDF indirmeleri |
| Geçmiş | Okunabilir kimlikler, filtreler, ayrıntı, karşılaştırma, sağlık eğilimi ve kalıcı silme |
| İşler | Kalıcı tek seferlik işler, aralıklı tekrar, iptal, yeniden deneme, ilerleme ve güvenli loglar |
| AI | İsteğe bağlı yerel veya açık onaylı uzak danışman analizi; varsayılan kapalı |
| Diller | İngilizce, Türkçe, Almanca, Fransızca, Basitleştirilmiş Çince ve İtalyanca dashboard etiketleri |
| Kurulum | Windows, macOS ve Linux’ta makine-yerel Host Service |

OCR, anlamsal kopya analizi, kimlik doğrulamalı Microsoft Graph kitaplık keşfi, vektör veri tabanı
içerik connector’ları, cron/takvim zamanlaması, ayarlanabilir saklama, çok kullanıcılı kimlik
doğrulama ve Docker dağıtımı henüz yoktur. Bir platformun bulunması içerik erişimi veya değerlendirme
anlamına gelmez.

## Kurun ve açın

Resmî depodan kurup makine servisini oluşturun:

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

Kurucu yerel dashboard’u açar. Daha sonra şunları kullanın:

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

Makine kurulumu ve yaşam döngüsü komutları yönetici izni gerektirir. Dashboard varsayılan olarak
yalnızca `127.0.0.1` üzerinde çalışır ve tek sabit adresi `http://localhost:8765` olur. Hosts dosyasını
değiştirmez; özel bir hostname veya port kabul etmez. Yerel yönetici şifresini Ayarlar’dan
değiştirebilirsiniz; bu işlem diğer tüm açık dashboard oturumlarını kapatır.

## Güncelleyin, onarın veya kaldırın

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update`, resmî `main` çalışma zamanını kurar; ayarları, gizli bilgileri, işleri ve raporları korur.
`repair`, çalışma zamanını ve servis kaydını yeniden oluşturur. `uninstall` yerel veriyi varsayılan
olarak korur; `--purge-data` kalıcı olarak siler.

## İçeriği tarayın

Önerilen arayüz dashboard’dur. Otomasyon veya doğrudan yerel taramalar için:

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

İş oluşturma çekmecesi şunları destekler:

- yerel dosya ve klasörler;
- açık içerik onayından sonra OpenWebUI bilgi tabanları;
- tek bir HTTPS sayfası veya desteklenen belge;
- aynı kaynaklı URL sitemap’leri ve bir iç içe sitemap-index seviyesi;
- isteğe bağlı bearer-token ortam referansıyla doğrudan erişilebilir SharePoint URL’leri;
- tek seferlik çalışma veya aralıklı izleme.

İş oluşturma dört adımlı yönlendirmeli bir akıştır: bağlı veya manuel kaynağı seçin, yalnızca o
kaynağın bilgilerini girin, tek seferlik ya da periyodik zamanlamayı belirleyin ve isterseniz AI'ı
açın. Periyodik işler için ilk yerel tarih ve saat seçilebilir. Yerel AI sağlayıcıları otomatik
kontrol edilir; doğrulanan modeller tek bir seçim alanında, uç nokta, kimlik bilgileri ve manuel
model girişi ise isteğe bağlı bağlantı ayarlarında gösterilir.

Uzak web taramaları yönlendirmeleri ve farklı kaynaklı sitemap kayıtlarını reddeder, betik çalıştırmaz
ve sayfa, yanıt boyutu ile zaman aşımı sınırları uygular. Kimlik doğrulamalı Microsoft Graph
site/kitaplık keşfi ayrı ve planlanan bir connector’dır.

## RAG yapılandırması ve doğrulama

Her yeni rapor seçilen iş yükü profilini kaydeder ve mevcut chunk ayarını gözlenen chunk
istatistikleriyle karşılaştırır. Olgu arama, genel soru yanıtlama, politika/prosedür, uzun bağlamlı
araştırma, kod veya tablo kullanımı için açıklanabilir bir başlangıç aralığı; bindirme ve ilk getirme
top-k değeri önerir. Evrensel bir en iyi chunk boyutu yoktur; rapor temsili sorgularla doğrulanması
gereken getirme, yanıt, atıf, gecikme ve maliyet metriklerini her zaman listeler.

Doğrudan ve kuyruğa alınan CLI taramalarında `--rag-profile` ile isteğe bağlı model bağlamı/top-k
seçeneklerini veya `ragscanner.toml` içindeki `[rag]` tablosunu kullanın. Ayrıntılar:
[RAG configuration advice](docs/rag-configuration-advice.md). Etiketli yerel bir külliyatı
`ragscanner quality calibrate` ile ölçebilirsiniz; bkz. [Quality calibration](docs/quality-calibration.md).
Altı dilli yerleşik külliyat yalnızca regresyon kontrolüdür, üretim doğruluğu kanıtı değildir.

## AI destekli raporlar

AI analizi isteğe bağlıdır ve deterministik bulguların yerini almaz. Ayarlar; eski bir model adını
tutmak yerine Ollama, LM Studio, LocalAI veya vLLM’de kurulu modelleri bulur. Uzak sağlayıcılar HTTPS,
harici kimlik bilgisi referansı ve tarama başına açık onay gerektirir.

Seçilen modele yalnızca sınırlandırılmış ve maskelenmiş bulgu özeti gönderilir; ham belgeler ve bulgu
kanıtları gönderilmez. Çıktı şemayla doğrulanır. Yerel uyumlu sunucu yapılandırılmış çıktı alanlarını
HTTP 400 ile reddederse JSON uyumluluk modunda bir kez denenir; o da başarısızsa açıklayıcı hata kodu
kaydedilir. Yaygın şema sapmaları normalleştirilir, uydurulan bulgu referansları güvenle atılır ve
kabul edilen analiz her gerçek bulguya düzeltme ile doğrulama adımları bağlayabilir.

## Raporlar ve işletim

Genel bakış sağlığı her zaman kalan en yeni tamamlanmış raporu kullanır. Raporlar filtrelenebilir,
tarihe göre karşılaştırılabilir, ayrıntılı incelenebilir veya onaydan sonra kalıcı silinebilir. Tek
seferlik işler ve tekrarlanan tanımlar ayrı gösterilir. Aktivite bölümü, ham sağlayıcı yanıtı veya
kimlik bilgisi göstermeden kararlı başarı/hata kodlarını ve güvenli nedenleri sunar.
Tekrarlanan planların sonraki çalışma zamanı ve aralığı düzenlenebilir. Raporlar güvenlik, içerik
kalitesi ve verimlilik puanlarını; dosya/sayfa/satır konumunu ve vurgulanan kanıtı gösterir. Her yerde
aynı eşikler kullanılır: 85 altı sarı, 70 altı turuncu, 55 altı kırmızı. AI analizi yavaş yerel
modeller için varsayılan olarak 180 saniye bekler; sağlayıcı hataları ve rapor verileri seçili dili izler.
Kaydedilen her rapor ayrıntı sayfasından ağ erişimsiz bağımsız HTML, çok sayfalı Excel çalışma
kitabı veya sayfalı PDF olarak indirilebilir. Dışa aktarımlar seçili arayüz dilini kullanır; kaynak
kanıtı özgün dilinde korunur.
Yeni taramalar kesme işareti gibi kaynak noktalama işaretlerini panel ve PDF kanıtında doğru korur.
Doğal olarak kısa tek belgeli yanıtlar ve yalnız normalleştirmeden doğan yaklaşık konumlar chunk
hatası olarak raporlanmaz.
Varyasyon testleri ayrıca üretilmiş başlık, liste, tablo, kod, bindirme, büyük/küçük harfsiz yazı
sistemleri ve küçük kelime örneklerinin kaynak kanıtı olmadan bulgu oluşturmasını engeller.

Yararlı işletim komutları:

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

Gelişmiş seçenekler için [tam CLI referansına](docs/cli.md), [dashboard rehberine](docs/dashboard.md)
ve [sorun giderme rehberine](docs/troubleshooting.md) bakın.

## Gizlilik ve güvenlik

- Statik yerel taramalar varsayılan olarak çevrimdışıdır ve LLM gerektirmez.
- Uzak belge veya model erişimi görünür yapılandırma ve açık onay gerektirir.
- API anahtarları SQLite dışında, sahibinin okuyabildiği makine dosyalarında veya `env:` referanslarında tutulur.
- Kalıcı işler ve raporlar yalnızca opak gizli bilgi referanslarını içerir.
- Ayrıştırılmış içerik, model çıktısı, URL’ler ve rapor kanıtı güvenilmeyen ve sınırlı veri sayılır.
- Ürünün ürettiği arayüz etiketleri yerelleştirilir; kaynak kanıtı özgün dilinde kalır.

Yeni entegrasyonları açmadan önce [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) ve
[source connector sözleşmesini](docs/source-connector-contract.md) okuyun.

## Katkıda bulunanlar için

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

Değişiklik göndermeden önce [CONTRIBUTING.md](CONTRIBUTING.md) içindeki Ruff, format, mypy, test ve
`uv build` kontrollerini çalıştırın. Mimari sınırlar [ARCHITECTURE.md](ARCHITECTURE.md), güncel
özellik durumu [docs/status/current.md](docs/status/current.md) içindedir.

## Lisans

Apache-2.0. [LICENSE](LICENSE) dosyasına bakın.
