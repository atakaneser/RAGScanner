# ADR-0015: OpenAI-compatible target desteği

- Status: Accepted
- Date: 2026-07-12

## Bağlam

OpenAI, Hugging Face TGI, vLLM, LiteLLM, NIM ve başka gateway’ler OpenAI benzeri chat protokolü sunabilir; uyumluluk ayrıntıları aynı değildir.

## Karar

Generic REST adapter’dan sonra OpenAI-compatible TargetAdapter uygulanır. Base URL, model, auth reference, Chat Completions/Responses capability, streaming ve tool-event desteği açıkça keşfedilir veya yapılandırılır. Ambient credential endpoint’i otomatik etkinleştirmez.

OpenAI-compatible olmak hedefin RAG olduğunu kanıtlamaz. Retrieval capability doğrulanmıyorsa target `llm` veya `unknown_retrieval` olarak raporlanır ve RAG-specific testler not-assessed kalır.

## Sonuçlar

Ortak protokol geniş platform erişimi sağlar. Tier 1 yalnız platform/version fixture’larıyla ilan edilir; “compatible” marka iddiası yeterli değildir.

