# Yol haritası

Tüm kilometre taşları ücretsiz ve açık kaynaktır.

## Milestone 0 — Ürün temeli

Ürün belgeleri, mimari, scanner/security modeli, issue backlog, monorepo yapısı, Apache-2.0 lisansı
ve açık kaynak governance. **Durum: tamamlandı.**

## Milestone 1 — Scanner Core

Python scaffold, CLI, document/finding modelleri, TXT/Markdown/PDF/DOCX, normalization, chunking, persistence ve raporlar. **Durum: ingestion'dan static security/quality/scoring ve terminal/JSON/HTML report'a unified offline scan tamamlandı; OCR ve persistence yok.**

The first usability slice now includes English bare-command onboarding, bounded local source
discovery, and consent-based OpenWebUI service-candidate checks. The next slices cover PDF/path
resilience, installation, and report UX.

## Milestone 2 — RAG Security Scan

Static rule engine yanında active endpoint testing: sürümlü prompt-injection/data-leakage/function-abuse/context-manipulation payload’ları, generic target adapter, deterministic response analyzer, rate limit/timeout/budget, TP/FP fixture ve güvenli security reports. **Durum: İlk deterministic static rule engine/pack/CLI ile TargetAdapter, safe active test library, Generic REST transport, response evaluation, in-memory active runner ve ortak reporting tamamlandı; persistence ve ek adaptörler yok.**

## Milestone 3 — RAG Health Scan

Exact/near/semantic duplicate, chunk quality, freshness, version conflict, metadata quality, Health Score ve RAG Rot. **Durum: exact normalized-content duplicate, bounded lexical near-duplicate ve deterministic chunk-quality analizleri tamamlandı; semantic duplicate, freshness, conflict, metadata quality, birleşik Health Score ve RAG Rot yok.**

## Milestone 4 — BYOM ve ileri analiz

Local embeddings, OpenAI-compatible/Ollama/OpenWebUI model endpoint, model doctor, balanced/deep mode, contradiction verification ve answer faithfulness. **Durum: başlanmadı.**

## Milestone 5 — Web dashboard

Overview, knowledge bases, scans/detail/comparison, findings/detail, schedules, connectors, settings ve about. **Durum: başlanmadı; yalnız uygulama dizini ayrıldı.**

## Milestone 6 — OpenWebUI entegrasyonu

OpenWebUI discovery/manual/scheduled scan yanında platform uyumluluk katmanı: OpenAI vector stores, Hugging Face TGI, generic OpenAI-compatible target, Ollama/vLLM/LiteLLM/NIM ve öncelikli vector-store connector’ları. **Durum: başlanmadı; yalnız connector paket sınırı ayrıldı.**

## Milestone 7 — Paketleme ve sürüm

Docker/Compose, install scripts, CI, package publishing, docs website ve security hardening. **Durum: temel CI mevcut; Docker/Compose ve yayın yok.**
