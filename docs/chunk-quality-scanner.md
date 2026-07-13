# Chunk-quality scanner

`ChunkQualityScanner`, mevcut chunk'ları offline ve deterministik heuristiklerle değerlendirir. Chunk
oluşturmaz veya değiştirmez; ideal retrieval kalitesini, doğruluğu ya da semantik tutarlılığı
kanıtlamaz.

## Kontroller

- boş, çok kısa, çok uzun, aykırı boyutlu veya karakter limitine yaklaşan chunk
- table/code/list/forced split warning'leri ve approximate source mapping
- heading context eksikliği veya ilgisiz heading branch'leri
- cümle ortasında başlayan/biten içerik ve noktalama/sayı/page-number ağırlığı
- tekrar eden satır/token, düşük bilgi yoğunluğu ve boilerplate baskınlığı
- replacement/control marker, düşük printable oranı ve garbled extraction sinyalleri
- komşu chunk overlap'ı, near-identical komşular ve aşırı chunk sayısı

Kontroller yapı metadata'sı yoksa bunu kesin hata gibi sunmaz; yalnız değerlendirilebilen sinyallerden
finding üretir. Eşikler `ChunkQualityConfig` ile değiştirilebilir. CLI `--min-chunk-tokens` ve
`--max-chunk-tokens` seçeneklerini doğrudan sunar.

## Puan

Her chunk için 0–100 aralığında `size_quality`, `structural_integrity`, `information_density`,
`overlap_efficiency`, `source_mapping_quality` ve `extraction_quality` boyutları ile açıklamalı bir
overall puan üretilir. Bu ürün tanımlı, sürümlü bir heuristic puandır; model benchmark'ı veya genel
bir endüstri standardı değildir. Eşik değişikliği karşılaştırmaları etkileyebilir.

Evidence bounded, HTML-escaped ve secret-masked'dir. Tam chunk rapora kopyalanmaz. Maksimum chunk,
finding, evidence ve çalışma süresi sınırları structured warning ve skipped item listesi üretir.
Network, subprocess, render, fetch, embedding veya LLM çağrısı yoktur.

