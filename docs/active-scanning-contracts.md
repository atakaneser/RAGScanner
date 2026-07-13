# Active scanning contract modelleri

Bu modeller transport veya scanner uygulaması değildir; network çağrısı yapmaz.

Vendor-neutral async port, capability, authorization, session, budget, redaction ve hata
semantiğinin güncel tanımı [`target-adapter-contract.md`](target-adapter-contract.md) içindedir.
`prepare_invocation` ağ çağrısı yapmaz; `invoke` yalnız transport sorumluluğu taşır ve
vulnerability değerlendirmesi yapmaz.

## Rol ayrımı

- `SourceConnector`: Document, chunk, metadata ve knowledge-base içeriği okur.
- `TargetAdapter`: Yetkili çalışan RAG/LLM uygulamasına black-box test gönderir.
- `ModelProvider`: RAGScanner’ın opsiyonel dahili analiz modelini sağlar.

Bu roller aynı platformda bulunsa bile ayrı config, credential reference ve provenance kullanır. OpenWebUI bir adapter’dır, core değildir. OpenAI/Hugging Face endpoint’i retrieval kanıtı değildir.

## TargetDefinition

Target türleri `generic_rest`, `openai_compatible`, `huggingface_inference`, `openwebui`, `custom` değerleriyle sınırlıdır. `authentication_reference` yalnız şu external secret reference biçimlerini kabul eder: `env:`, `keychain:`, `secret-manager:`, `vault:`, `file-secret:`.

Request template, response mapping, header ve metadata içine raw API key, token, password veya credential gömülemez.

## AuthorizationScope ve SafetyMode

Active Scan açık authorization olmadan geçersizdir. Authorized scope actor, timezone-aware time, description ve environment gerektirir. Expiration doğrudan sorgulanabilir.

Safety mode varsayılan `safe` değeridir. `destructive` hiçbir zaman örtük seçilemez. Safe-default test case destructive side-effect veya production-unsafe payload içeremez.

## Test case ve payload

`SecurityTestCase`; severity, detection type, payload variants, safe/unsafe/ambiguous indicator’lar, control payload, tool access ve side-effect riskini taşır. Payload’lar language/encoding/tag ve production safety metadata içerir; Türkçe ve İngilizce aynı sözleşmeyi kullanır.

## Request, response ve execution

`TargetRequest` raw secret içeren header/body/metadata kabul etmez. `TargetResponse` oluşturulmadan önce header ve body redakte/truncate edilmelidir. `TestExecution` request/response summary içinde raw secret kabul etmez ve lifecycle zaman sırasını doğrular.

Execution durumları: `pending`, `running`, `completed`, `failed`, `skipped`, `cancelled`.

Provider-neutral orchestration lifecycle, selection, budget, control ve finding politikası
[`active-scan-runner.md`](active-scan-runner.md) içinde tanımlıdır. Runner persistence veya UI
katmanı değildir.

## Evaluation

Evaluation classification: `confirmed`, `probable`, `ambiguous`, `not_detected`, `inconclusive`. Evaluator type: `deterministic`, `heuristic`, `llm_assisted`, `manual`. Evidence raw secret içeremez ve manual-review ihtiyacı açık alandır.

Uygulanan deterministic/heuristic/control-comparison ve composite precedence ayrıntıları
[`response-evaluation-engine.md`](response-evaluation-engine.md) içindedir. LLM-assisted katman
yalnız protokoldür.

## Secret içermemesi gereken alanlar

- `TargetDefinition.request_template`, `response_mapping`, `headers`, `metadata`
- `TargetRequest.headers`, `body`, `metadata`
- `TargetResponse.headers`, `body`, `transport_error`, `metadata`
- `EvaluationResult.evidence`, `metadata`
- `TestExecution.request_summary`, `response_summary`, `metadata`
- `Finding.evidence`, `metadata`
- `Scan.metadata`

Helper’lar caller nesnesini değiştirmeden control character normalizasyonu, secret masking, header redaction ve bounded truncation döndürür.
