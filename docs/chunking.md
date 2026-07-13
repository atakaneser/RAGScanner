# Document chunking

Chunker yalnız `Document` ve ona ait, hash'i doğrulanmış `NormalizationResult` kabul eder. Original
ve normalized belgeyi mutate etmez; mevcut `Chunk` domain modelinden deterministik çıktı üretir.
Chunking summarization, sanitization, duplicate detection veya security scanning değildir. Şüpheli
talimatlar korunur; render, execute, fetch, network, subprocess, embedding veya LLM çağrısı yoktur.

## Stratejiler

- `structure_aware` (varsayılan): Section/page, heading hierarchy, paragraph, list/table/code
  annotation ve ardından sentence/token fallback kullanır.
- `paragraph_aware`: Paragraph sınırlarını temel alır; hard size limitinde aynı bounded fallback'i
  kullanır.
- `token_window`: Yapısal metadata bulunmadığında veya açıkça seçildiğinde deterministic token
  penceresi uygular.

Structure-aware mod heading'i takip eden içerikle birlikte tutar ve parent heading path'i
`Chunk.headings` alanına koyar. İlgisiz top-level heading branch, farklı section ve varsayılan olarak
farklı page birleşmez. Table/list/code blokları mümkün olduğunda atomik kalır. Tek blok hard limiti
aşarsa önce sentence sonu, bulunamazsa token window kullanılır; `forced_split` ile birlikte
`table_split`, `code_block_split` veya `list_split` warning'i oluşur. İçerik truncate edilmez.

## Varsayılan yapılandırma

- target 300, maximum 500, minimum 50 approximate token
- overlap 30, hard maximum overlap 100 token
- chunk başına 100.000 karakter safety limiti
- document başına 5.000.000 karakter, 100.000 block ve 10.000 chunk limiti
- page/table/code preservation, heading context ve small-section merge açık

Bu değerler bilimsel veya her model için optimal değildir. Belge türü, retrieval modeli, gerçek
tokenizer ve latency hedefleri farklı configuration gerektirir. Config'in tamamı provenance ve
stable-ID identity'sine dahil edilir.

## Token sayımı ve overlap

İlk tokenizer vendor-neutral Unicode word + punctuation approximation'dır. Model-specific BPE ile
aynı sayı değildir; sonuç `tokenizer_approximation` warning'i taşır. Core `TokenCounter` protokolü
sayesinde belirli model/vendor'a bağlı değildir.

Overlap kapatılabilir, maksimum chunk boyutunu aşamaz ve önceki chunk'ın tamamını kopyalamaz.
Farklı page/section/top-level heading branch arasında uygulanmaz. Table/code sınırında full block
tekrarı riski nedeniyle azaltılır veya atlanır ve `overlap_reduced` üretilir.

## Stable ID ve mapping

Chunk ID; namespace/version, document ID, normalized hash, chunker/tokenizer sürümü, tam config
identity, index, normalized range ve normalized içerikten SHA-256 üretilir. Timestamp içermez. Aynı
input/config/sürümler aynı ID'leri; config veya algorithm version değişikliği farklı ID üretir.

Her chunk normalized ve original start/end, source identity/path, line span, ilk page, page range,
section range ve DOCX parser block listesini taşır. Normalization segmenti approximate ise chunk da
`approximate_source_mapping=true` ve warning taşır. `Chunk.content` original parsed range,
`Chunk.normalized_content` indexing/scanning görünümüdür. Non-overlap chunk aralıkları normalized
belgenin tamamını sırasıyla kapsar.

## Sınırlamalar

- Approximate tokenizer model context limitini kesin garanti etmez.
- Sentence detection bounded punctuation heuristic'idir.
- Büyük table/code blokları hard limitte bölünebilir fakat bu hiçbir zaman sessiz olmaz.
- Overlap bilinçli tekrar oluşturabilir; metadata ile işaretlenir.
- Maximum chunk limiti aşılırsa partial/lossy sonuç yerine typed error döner.
- Chunker finding üretmez; çıktısı ayrı [static security scanner](static-security-scanner.md)
  ve [chunk-quality scanner](chunk-quality-scanner.md) tarafından tüketilebilir. Ayrı
  [duplicate scanner](duplicate-detection.md) normalized chunk içeriğini analiz eder. Persistence,
  index upload, report veya embedding üretmez.
