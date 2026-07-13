# Güncel durum

**Aşama:** Milestone 1 — scaffold, core domain ve static source kontratları  
**Sürüm:** package/tag olarak yayınlanmadı (`0.1.0a1` alpha candidate)  
**Repository:** `https://github.com/atakaneser/RAGScanner` üzerinde ilk public baseline

## Mevcut çalışan kapsam

- `uv` ile kilitlenen Python 3.12+ src-layout paket
- Typer CLI, Pydantic environment config ve structured logging
- `ragscanner --version` ve network kullanmayan `ragscanner doctor`
- Framework-bağımsız static modeller: `SourceLocation`, `Document`, `Chunk`
- Active kontratlar: target, authorization, safety, payload/test-case, request/response, execution/evaluation
- Ortak `Finding`, `Scan` ve `ScoreSummary`
- Explicit enum, timezone-aware datetime ve mutable-default doğrulamaları
- Deterministic SHA-256 content hash/fingerprint helper’ları
- Control normalization, secret masking, header redaction ve bounded truncation helper’ları
- pytest, Ruff, strict mypy ve GitHub Actions
- Vendor-neutral async `SourceConnector`, typed source/error/pagination/change modelleri
- Yalnız test desteği için deterministik, bellek içi ve ağ/dosya sistemi erişimsiz fake connector
- Vendor-neutral async `TargetAdapter`; capability, invocation/observation, session, budget ve typed error modelleri
- Yetki, safe-mode, canary/no-op tool davranışı, destructive capability ve bütçe uygulayan deterministik test fake'i
- Sekiz kategoride versioned JSON active security test library, typed loader ve placeholder renderer
- Duplicate/unsafe/destructive/credential/real-target doğrulamaları ve deterministic filtreleme
- Async `httpx` kullanan provider-neutral Generic REST Target Adapter
- Declarative JSON template/dotted mapping, secret resolver ve SSRF/redirect/TLS/timeout/size/budget/cancellation kontrolleri
- Deterministic + explainable heuristic response evaluator, typed control comparison ve composite precedence
- Provider-neutral LLM-assisted evaluator protokolü; gerçek model çağrısı yok
- Provider-neutral sequential active scan runner; plan/result/event, control, budget, cancellation ve finding üretimi
- Root-confined local filesystem SourceConnector; TXT/Markdown discovery, bounded content ve snapshot change detection
- Plain-text ve non-rendering Markdown parser; valid `Document`/`ParserResult`, front matter title ve heading metadata
- PyMuPDF tabanlı bounded text PDF parser; page offset map, metadata, scanned/quality/active-content warning'leri
- python-docx tabanlı bounded DOCX parser; ordered block/offset metadata ve active/hidden/external-content warning'leri
- Deterministic NFC-default document normalizer; conservative whitespace/PDF repair, structural annotation ve bounded original-source mapping
- Deterministic structure/paragraph/token-window chunker; vendor-neutral token approximation, bounded overlap, stable ID ve source mapping
- Versioned JSON static security rule engine ve 10 kategorilik ilk rule pack; offline matcher, context-aware FP adjustment, bounded/redacted Finding ve CLI
- Exact normalized-document/chunk duplicate scanner; stable canonical grouping ve redundant-content tahmini
- Bounded lexical shingle/Jaccard near-duplicate scanner; boilerplate-aware imza ve manual-review findings
- Deterministic chunk-quality scanner; yapı, boyut, yoğunluk, overlap, mapping ve extraction boyutları
- `ragscanner quality scan` terminal/JSON CLI; scanner filtreleri, eşikler ve `--fail-on`
- Static/active/combined aggregate için boundary redaction, deterministic filtre/sıralama ve typed report modeli
- Terminal, v1 JSON Schema ve external asset/script içermeyen standalone HTML reporter
- `ragscanner report` CLI ve tamamen sentetik sample input/terminal/JSON/HTML preview
- Filesystem → parser registry → normalization → chunking → security/duplicates/quality → scoring → reporting unified static pipeline
- `ragscanner scan` CLI; strict local TOML, CLI override, progress/cancellation, stable exit codes ve atomic output
- TXT/Markdown yanında PDF/DOCX discovery ve bounded binary retrieval destekleyen filesystem connector
- Tamamen sentetik multilingual `examples/sample-kb` quickstart bilgi tabanı
- Tek TXT/Markdown/PDF/DOCX root ve 2–4+ küçük koleksiyon için source-count/assessment coverage
- PEP 440 `0.1.0a1`, bundled wheel rule/schema resources ve alpha build/smoke workflow

## Henüz bulunmayanlar

OCR, semantic duplicate scanner, freshness/contradiction/metadata-quality analizleri, birleşik Health/RAG Rot score, diğer SourceConnector/TargetAdapter adaptörleri, ModelProvider/OpenWebUI kodu, persistence, API, dashboard, worker, scheduler, gerçek LLM-assisted evaluation ve Docker deployment.

Domain modelleri scan yapmaz ve hiçbir network/filesystem erişimi içermez.

## Önerilen sonraki issue

`RS-014 persistence schema`: Unified scan sonuçları için SQLite-first history/migration tasarımı; otomatik başlanmamalıdır.

## Alpha release durumu

Apache-2.0 lisansı, canonical `https://github.com/atakaneser/RAGScanner` repository'si ve private
GitHub Security Advisory kanalı onaylanmıştır. Alpha package/tag yayını için son release
doğrulaması ayrıca tamamlanmalıdır. Ayrıntılar
[`docs/release-readiness-v0.1.0-alpha.1.md`](../release-readiness-v0.1.0-alpha.1.md) içindedir.
