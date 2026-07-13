# ADR-0011: SourceConnector, TargetAdapter ve ModelProvider ayrımı

- Status: Accepted
- Date: 2026-07-12

## Bağlam

Filesystem, vector store, OpenWebUI, OpenAI ve Hugging Face gibi sistemler document source, test target veya analiz modeli rollerinden birini ya da birkaçını sağlayabilir. Bu rollerin tek “provider” arayüzünde birleşmesi credential, consent ve dependency sınırlarını bozar.

## Karar

Entegrasyonlar üç bağımsız port kullanır:

- `SourceConnector`: document/chunk/metadata/knowledge-base içeriği okur.
- `TargetAdapter`: yetkili çalışan RAG/LLM uygulamasına black-box test gönderir.
- `ModelProvider`: scanner’ın opsiyonel dahili analiz modelini sağlar.

Aynı platform farklı rollerde kullanılsa bile ayrı config, credential reference ve provenance taşır. LLM endpoint’i retrieval kanıtı değildir; yalnız doğrulanan retrieval pipeline `rag` target etiketini alır. OpenWebUI core değil, adapter’dır.

## Sonuçlar

Daha fazla contract fixture gerekir fakat core vendor bağımsız kalır; source erişimi model kullanımını veya active testi örtük etkinleştiremez.

