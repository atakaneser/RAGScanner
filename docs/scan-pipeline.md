# Unified static scan pipeline

`StaticScanPipeline`, local filesystem kaynağını mevcut ingestion, security, quality ve reporting
sözleşmelerine bağlayan framework-bağımsız orchestration servisidir:

```text
filesystem → discovery/read → parser registry → normalize → chunk
           → static security + exact/near duplicate + chunk quality
           → product-defined scores → report-ready result
```

TXT, Markdown, text-based PDF ve DOCX explicit registry ile seçilir; dynamic import veya plugin
çalıştırılmaz. Her dosya retrieval/parsing/normalization/chunking aşamalarından bağımsız geçer. Bir
dosyanın hatası sonraki aşamasını durdurur fakat diğer dosyalar devam eder. Collection scanner
hataları typed `StageError` olur ve bağımsız scanner'lar çalışmaya devam eder.

Bir TXT/Markdown/PDF/DOCX dosyası doğrudan root olarak verilebilir. Bu durumda parent directory
security root olur fakat yalnız exact filename discover edilir. Rapor `single_source` ve source
count gösterir. Intra-document repeated/near-duplicate chunk kontrolleri çalışır; cross-document
duplicate, version conflict ve freshness kontrolleri veri yetersizliğinin gerekçesiyle
`not_assessed` olur. İki, üç veya dört kaynak normal `collection` modudur; cross-document exact/near
duplicate çalışır. Version conflict/freshness scanner'ı henüz olmadığı için bunlar yine açıkça
`not_assessed` kalır. Kaynak sayısının azlığı warning değildir.

## Status ve skor

- `completed`: anlamlı iş tamamlandı, fatal/operational hata yok.
- `completed_with_warnings`: file skip/failure, scanner hatası veya degrading warning var.
- `failed`: source unavailable, fatal initialization veya hiçbir document tamamlanmadı.
- `cancelled`: cooperative cancellation yeni item processing'i durdurdu.

Finding bulunması operational failure değildir. Security score static-security finding severity ×
confidence penalty'sinden; knowledge quality chunk-quality puan ortalamasından; efficiency duplicate
yüzdesinden hesaplanır. Overall yalnız assessed değerlerin ortalamasıdır. Bunlar RAGScanner
product-defined formülleridir. Retrieval quality, answer reliability, freshness ve RAG Rot `None`.

Progress event portu UI/WebSocket/storage bilmez. No-op ve ANSI kullanmayan terminal sink vardır.

## Exit kodları

- `0`: scan tamamlandı, fail-on tetiklenmedi
- `1`: operational/source/report-write failure
- `2`: CLI veya config hatası
- `3`: scan tamamlandı fakat `--fail-on` eşiği aşıldı
- `130`: kullanıcı iptali
