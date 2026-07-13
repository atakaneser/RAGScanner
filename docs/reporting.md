# Reporting engine

RAGScanner mevcut static, active veya combined scan sonuçlarından framework-bağımsız ve tamamen
offline rapor üretir. Reporting persistence, FastAPI veya dashboard modeli bilmez. `ReportInput`
mevcut `Scan`, `Finding`, `TestExecution`, score, duplicate group, chunk-quality ve scanner
istatistiklerini bir araya getirir; `ReportBuilder` bunların redakte edilmiş immutable görünümünü
oluşturur.

Unified `ragscanner scan` doğrudan bu aggregate'i üretip aynı terminal/JSON/HTML reporter'larını
kullanır; database veya fake result gerekmez.

Her unified report `knowledge_base_mode`, source count ve assessment coverage taşır. `not_assessed`
kontroller başarılı/zero-score gibi sunulmaz; neden çalışmadıkları terminal, JSON ve HTML'de yazılır.

Finding sırası deterministiktir: severity, classification, confidence azalan, category, source,
rule ID ve fingerprint. Severity, confidence ve classification ayrı tutulur. Eksik skor
`null`/`Not assessed` olur; sıfıra çevrilmez. Skorlar “RAGScanner product-defined”, redundant
token/character kazancı tahmin olarak etiketlenir.

Rapor-time filtreleri severity, category, classification, document, target, rule ID, informational
inclusion ve maksimum finding'i destekler. Filtreler source sonucu mutate etmez ve raporda belirtilir.
Collection truncation sessiz değildir.

Evidence, metadata, header-benzeri key, credential URL, connection string, bearer/API key, cookie ve
private key rapor sınırında tekrar maskelenir. Absolute source path varsayılan basename olur.
Suspicious URL linke çevrilmez. Ağ, subprocess, analytics veya telemetry yoktur.

```bash
uv run ragscanner report input.json --format terminal --verbose
uv run ragscanner report input.json --format json --output report.json
uv run ragscanner report input.json --format html --output report.html
```

İmzalı/verified report OD-016 çözülene kadar uygulanmamıştır.
