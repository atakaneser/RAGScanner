# Ürün tanımı

## Amaç

RAGScanner; Retrieval-Augmented Generation sistemlerinde kullanılan bilgi, retrieval sonucu ve cevapların güvenli, güncel, güvenilir ve verimli olup olmadığını inceleyen ücretsiz ve açık kaynak bir platformdur. Yalnızca soyut skor üretmez; etkilenen kaynak, belge, sayfa, chunk, query, retrieval sonucu veya cevabı gösterir ve uygulanabilir remediation önerir.

Konumlandırma: **“Scan your RAG before your users do.”**

## Tek ürün modeli

RAGScanner tek public GitHub repository’de geliştirilir. CLI, scanner core, API, worker, scheduler, dashboard, connector’lar, security rules, raporlar ve dokümantasyon ücretsizdir. Pro/Team/Enterprise edition, ödeme, Stripe, abonelik, entitlement, lisans sunucusu, private repository, paid rule feed veya yapay özellik limiti yoktur.

## Kullanım biçimleri

- Yerel klasörü tek sefer tarama
- Offline güvenlik ve sağlık analizi
- Yerel/self-hosted dashboard üzerinden tarama ve geçmiş
- Taramaları karşılaştırma ve zamanlama
- OpenWebUI knowledge base bağlantısı
- Değişiklik algılandığında yeniden tarama
- Opsiyonel kullanıcı modeli ve yerel embedding
- Terminal, JSON, HTML ve dashboard raporları

## Analiz modları

- **Offline:** Chat LLM çağrısı yoktur; deterministik ve heuristic kontroller ile opsiyonel yerel embedding kullanılır.
- **Balanced:** Yerel kurallar adayları daraltır; yalnızca açıkça yapılandırılmış modele minimum ve redakte edilmiş excerpt gönderilir.
- **Deep:** Synthetic test, contradiction verification ve answer faithfulness gibi daha maliyetli analizler çalıştırılabilir. Bu mod da ücretsizdir; model/altyapı kullanıcıya aittir.

## RAG Security Scan

Security Scan, Milestone 2’nin ve ürün kimliğinin çekirdek parçasıdır. Aşağıdaki sınıfları kapsar:

- indirect prompt injection,
- instruction override ve system prompt extraction,
- model manipulation ve tool invocation,
- shell/script/embedded command talimatları,
- hidden veya invisible text,
- HTML comment içindeki model talimatları,
- Base64 ve encoded payload,
- suspicious URL ve malicious document content,
- data poisoning ve metadata manipulation,
- secret/API key/credential/connection string,
- PII exposure,
- cross-tenant ve access-control retrieval riskleri.

Security finding; severity ve confidence’ı ayrı tutar; detection class (`deterministic`, `heuristic`, `llm_assisted`) içerir; kaynak belge, varsa page/chunk, redakte evidence, risk, remediation, scanner rule/version ve fingerprint taşır. LLM-assisted sonuç, deterministik kanıt yoksa “confirmed vulnerability” olarak gösterilmez.

Security Scan iki tamamlayıcı çalışma biçimine ayrılır:

- **Static/Passive Scan:** Belge, chunk ve metadata içindeki prompt injection, hidden instruction, secret, PII, poisoning ve zararlı içerik sinyallerini yerel olarak inceler.
- **Active/Dynamic Scan:** Kullanıcının açıkça yetkilendirdiği çalışan RAG/chat endpoint’ine sürümlü saldırı payload’ları gönderir; prompt injection, system prompt extraction, data leakage, tool/function abuse ve context manipulation davranışlarını gözlemler.

Active Scan yalnız hedef sahibi tarafından yetkilendirilmiş endpoint’lerde çalıştırılır. Demo modu gerçekmiş gibi vulnerability üretmez. Payload, target response ve response analyzer sürümlenir; rate limit, timeout, request budget, cancellation ve redaksiyon zorunludur.

Static knowledge scanning ile active endpoint scanning ayrı scan mode’larıdır; biri diğerinin yapıldığını ima etmez. Active Scan varsayılan olarak `safe` profile kullanır. Destructive veya side-effect-capable payload’lar varsayılan etkinleştirilemez; tool-use testleri canary, dry-run veya no-op action kullanır.

## Platform uyumluluğu

RAGScanner üç bağımsız adapter ailesi kullanır:

1. `SourceConnector`: Dosya, document, chunk ve retrieval metadata alır.
2. `TargetAdapter`: Çalışan RAG/chat uygulamasına aktif güvenlik testleri gönderir.
3. `ModelProvider`: RAGScanner’ın opsiyonel gelişmiş analizinde kullanılacak modeli sağlar.

Bir platform bu rollerden birini veya birkaçını üstlenebilir; roller birbirine bağlanmaz. Örneğin OpenWebUI belge kaynağı kullanılırken Ollama model provider seçilebilir veya OpenAI vector store taranırken LLM analizi tamamen kapalı tutulabilir.

Bir LLM endpoint’i tek başına RAG değildir. OpenAI veya Hugging Face kullanılması retrieval yapıldığının kanıtı sayılmaz. Target yalnız test edilen uygulamanın gerçekten retrieval yaptığı doğrulanırsa “RAG target” olarak adlandırılır. OpenWebUI desteklenen entegrasyonlardan biridir; ürün core’u veya zorunlu runtime değildir.

Active response evaluation `confirmed`, `probable`, `ambiguous` ve `not_detected` durumlarını ayırır. `not_detected` güvenlik garantisi değildir; broad keyword veya tek model yorumu `confirmed` üretemez.

Planlanan uyumluluk:

- Generic OpenAI-compatible Chat Completions/Responses target
- OpenAI vector stores/File Search source
- Hugging Face TGI ve Inference Endpoint target/model
- OpenWebUI source ve target/model rolleri ayrı
- Ollama, vLLM, LiteLLM ve NVIDIA NIM
- Local filesystem
- Qdrant, Chroma, Weaviate, Pinecone, Milvus ve pgvector
- Generic REST target ve Python callback/SDK adapter’ı

## RAG Health Scan

Duplicate/near duplicate/semantic duplicate, empty/malformed content, chunk kalite problemleri, metadata eksikleri, freshness, aktif eski-yeni sürüm, source-index mismatch, contradiction candidate, retrieval ve answer kalite sinyallerini kapsar. Kaynak capability veya ground truth yoksa kontrol “not assessed” olur; başarılı sayılmaz.

## Skorlar

RAG Health Score ve RAG Rot ürün tanımlı, yapılandırılabilir ve sürümlü metriklerdir. Bilimsel standart değildir. Kritik security finding genel skoru sınırlayabilir; skor coverage, skipped/failed check ve policy version ile raporlanır.

## Yerel kullanım ve kimlik doğrulama

İlk dashboard tek kullanıcılı, localhost/private-network self-hosted kullanım içindir. Public registration, organization, membership, RBAC, SSO, subscription ve entitlement modeli ilk sürümde yoktur. Localhost dışına açılan kurulumlar reverse proxy authentication, VPN veya private network ile korunmalıdır. Uygulama auth’u daha sonra opsiyonel ve bağımsız eklenebilir.

## Başlangıç dışı kapsam

- Multi-tenant SaaS
- Public signup ve hesap yönetimi
- Microservice mimarisi
- Kubernetes zorunluluğu
- Her vector database’i ilk sürümde desteklemek
- Otomatik kaynak düzeltme veya payload çalıştırma
- Skorları bilimsel doğruluk/güvenlik garantisi olarak sunma

## Başlıca riskler

- Security false positive yorgunluğu veya kaçırılan saldırıların yanlış güven üretmesi
- Parser, rule pack ve model supply-chain saldırıları
- Remote model kullanımında veri sızıntısı
- Encoded content çözümlemesinde kaynak tüketimi
- OpenWebUI API değişiklikleri
- Dashboard/scheduler kapsamının core scanner’ı geciktirmesi
- Açık kaynak bakım kapasitesi ve güvenlik disclosure süreçleri
