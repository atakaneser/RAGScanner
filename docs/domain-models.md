# Domain modelleri

RAGScanner domain katmanı `ragscanner.domain` altında Pydantic ile tanımlanır ve FastAPI, SQLAlchemy, Typer, HTTP client, filesystem veya UI bağımlılığı içermez.

## Static modeller

- `SourceLocation`: Source kimliği/türü/adı, path, page, section, line range ve metadata.
- `Document`: Original ve normalized content, SHA-256, MIME/language, timezone-aware zamanlar, metadata ve warnings.
- `Chunk`: Document/index kimliği, content/hash/count, source/headings ve metadata.

Original content modelleri scanner input’udur ve helper’lar tarafından sessizce değiştirilmez. `document_content_hash` UTF-8 içeriğin SHA-256 değerini üretir. Chunk kimliği document/index/normalized content yanında chunker, tokenizer ve tam config identity'sine bağlıdır.

## Normalizasyon modelleri

`NormalizationConfig` conservative ve bounded stage ayarlarını; `NormalizationResult` original ve
normalized hash, normalized content, segment, warning, annotation, statistics ve normalizer
version'ını taşır. `NormalizationSegment` normalized range'i original parsed range ve
`SourceLocation` ile ilişkilendirir; dönüşüm kayıplı veya birden-çoğa ise `approximate` olur.
`NormalizationAnnotation` invisible Unicode ile page/header/footer/code/table/list/heading gibi
aday ve structural span'ları metni silmeden gösterir. Normalizer `Document` nesnesini mutate etmez.

## Chunking modelleri

`ChunkingConfig`, structure/paragraph/token-window stratejileri ile token, character, overlap,
structure ve resource limitlerini taşır. `ChunkingResult`; mevcut `Chunk` modelleri yanında typed
warning, statistics, chunker/tokenizer version ve tam config provenance içerir. Chunk original ve
normalized metni ayrı tutar; normalized/original range, page/section/parser-block mapping, forced
split, overlap ve structure flag'leri metadata'dadır. Stable ID timestamp içermez; config veya
algorithm version değişikliği kimliği bilinçli olarak değiştirir.

## Ortak Finding modeli

Static ve active gözlemler aynı `Finding` modelini kullanır. Static finding source/document/chunk alanlarını; active finding target/test-case/execution alanlarını doldurur. Active referanslardan biri varsa üçü de zorunludur.

Üç eksen birbirinden ayrıdır:

- `severity`: Olası etkinin büyüklüğü.
- `confidence`: Kanıt gücü; 0–1.
- `classification`: `confirmed`, `probable`, `ambiguous`, `not_detected` veya `inconclusive`.

Severity yüksek olduğu için finding otomatik confirmed olmaz. `not_detected` güvenlik garantisi değildir.

## Scan ve skor

`ScanType`: `static`, `active`, `combined`. `AnalysisMode`: `offline`, `balanced`, `deep`. Scan lifecycle `pending`, `running`, `completed`, `completed_with_warnings`, `failed`, `cancelled` değerlerini kullanır.

Active/combined Scan geçerli, süresi dolmamış `AuthorizationScope` ve `target_id` olmadan kurulamaz. Safety mode varsayılan `safe` değeridir.

`ScoreSummary` alanları 0–100 aralığındadır; `None` “not assessed” anlamındadır.

## Unified pipeline modelleri

`StaticPipelineConfig` local source/limit/parser/normalization/chunking/scanner/output politikasını;
`StaticPipelineResult` scan, source health/descriptor, document/chunk, finding/group, scanner stats,
warning/error/skip, score ve cancellation durumunu taşır. `StageError` persistence ID içermez.
Static progress event'leri provider-neutral sink üzerinden yayınlanır.

## Fingerprint politikası

Fingerprint’ler canonical, namespace/version içeren JSON üzerinden SHA-256 ile üretilir:

- Document content hash içeriğe bağlıdır.
- Chunk fingerprint source/document/index/normalized-content’e bağlıdır.
- Finding fingerprint rule/version/source/document/chunk/target/test-case/evidence’a bağlıdır.
- Test execution fingerprint scan/target/test-case/payload’a bağlıdır.

Fingerprint algoritması değişirse namespace sürümü artırılmalıdır; geçmiş kimliklerle sessizce karıştırılmaz.

## Mutable defaults ve zaman

List/dict alanları `default_factory` kullanır. Tüm domain zamanları timezone-aware olmak zorundadır. Naive datetime validation hatasıdır.
