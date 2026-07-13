# RAGScanner

[English](README.md) · **Türkçe** · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner, RAG bilgi kaynaklarındaki güvenlik ve içerik kalitesi risklerini yerel olarak inceleyen,
ücretsiz ve açık kaynaklı bir araçtır. Mevcut teknik alpha; TXT, Markdown, metin tabanlı PDF ve DOCX
dosyalarını tarar, terminal, JSON veya bağımsız HTML raporu üretir.

> [!WARNING]
> Bu sürüm teknik alpha’dır. Statik tarama çalışan bir RAG uygulamasının güvenli olduğunu kanıtlamaz.
> Bulgular inceleme girdisidir; güvenlik garantisi değildir.

## Şu anda çalışan özellikler

- Tek dosya ve yerel klasör tarama
- TXT, Markdown, metin tabanlı PDF ve DOCX
- Deterministik normalizasyon, chunking ve kaynak eşleme
- Statik güvenlik kuralları
- Exact ve lexical near-duplicate analizi
- Chunk kalite kontrolleri
- Terminal, JSON ve bağımsız HTML raporları
- Varsayılan olarak tamamen yerel ve offline çalışma
- `ragscanner` komutuyla İngilizce yönlendirmeli başlangıç

OCR, persistence, API, dashboard, scheduler, OpenWebUI içerik connector’ı ve ModelProvider henüz
mevcut değildir.

## Kurulum ve ilk tarama

Python 3.12/3.13 ve [`uv`](https://docs.astral.sh/uv/) gereklidir.

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Doğrudan tarama:

```powershell
ragscanner scan "C:\Users\Example\Documents\Bilgi Tabanı"
ragscanner scan "C:\Users\Example\Downloads\Kılavuz (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Boşluk veya parantez içeren yolları tırnak içine alın. RAGScanner mevcut rapor dosyasının üzerine
varsayılan olarak yazmaz.

## Dil ve gizlilik

Ürün arayüzü, hata mesajları, remediation ve üretilen teknik metadata İngilizcedir. Taranan RAG
belgeleri Türkçe dahil tüm Unicode dillerinde olabilir. Kaynak kanıtı denetlenebilirliği korumak için
özgün dilinde gösterilir.

Statik tarama belge içeriğini dış servislere göndermez, LLM gerektirmez, telemetry çalıştırmaz,
bağlantıları takip etmez ve tespit edilen komutları yürütmez. Remote connector veya model kullanımı
ileride yalnız açık yapılandırma ve onayla etkinleşecektir.

## Mimari ve yol haritası

`SourceConnector`, `TargetAdapter` ve `ModelProvider` birbirinden ayrıdır. OpenWebUI desteklenecek
entegrasyonlardan biridir; ürünün çekirdeği değildir.

Sıradaki işler PDF/yol dayanıklılığı ve rapor UX, SQLite geçmişi, API, OpenWebUI connector’ı, yerel
dashboard ve scheduler’dır. Güncel ayrıntılar için kanonik [İngilizce README](README.md),
[ROADMAP.md](ROADMAP.md) ve [durum belgesine](docs/status/current.md) bakın.

RAGScanner [Apache License 2.0](LICENSE) ile lisanslanmıştır ve tamamen ücretsizdir.
