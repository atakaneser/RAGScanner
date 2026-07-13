# Platform uyumluluk planı

Bu belge planlanan uyumluluğu gösterir; mevcut scaffold henüz connector, target veya model provider içermez.

Bir platformun LLM üretmesi retrieval yaptığı anlamına gelmez. OpenAI ve Hugging Face model/endpoint sağlayabilir; RAG etiketi yalnız test edilen uygulamanın retrieval pipeline’ı doğrulandığında kullanılır. OpenWebUI bir entegrasyondur, RAGScanner core değildir.

## Roller

| Platform | SourceConnector | TargetAdapter | ModelProvider | İlk tier hedefi |
|---|---:|---:|---:|---|
| Local filesystem | Evet | Hayır | Hayır | Tier 1 |
| Generic OpenAI-compatible | Hayır | Evet | Evet | Tier 1 |
| OpenWebUI | Evet | Evet | Evet | Tier 1 |
| OpenAI | Vector store/File Search | Chat/Responses | Chat/Embedding | Tier 1 |
| Hugging Face TGI/Endpoint | Hayır | Evet | Evet | Tier 1/Tier 2 |
| Ollama | Hayır | Evet | Evet | Tier 1 |
| vLLM | Hayır | Evet | Evet | Tier 2 üzerinden OpenAI-compatible |
| LiteLLM | Hayır | Evet | Evet | Tier 2 üzerinden OpenAI-compatible |
| NVIDIA NIM | Hayır | Evet | Evet | Tier 2 üzerinden OpenAI-compatible |
| Qdrant | Evet | Hayır | Hayır | Tier 1 adayı |
| Chroma | Evet | Hayır | Hayır | Tier 1 adayı |
| Weaviate | Evet | Hayır | Hayır | Tier 2 adayı |
| Pinecone | Evet | Hayır | Hayır | Tier 2 adayı |
| Milvus | Evet | Hayır | Hayır | Tier 2 adayı |
| pgvector | Evet | Hayır | Hayır | Tier 2 adayı |
| Custom REST/Python callback | Capability’ye göre | Evet | Opsiyonel | Experimental |

## Tier tanımları

- **Tier 1:** Resmi sürüm matrisi, CI contract fixture ve maintainer doğrulaması.
- **Tier 2:** Generic protokol üzerinden beklenen uyumluluk ve community fixture doğrulaması.
- **Experimental:** API kararsız, eksik veya yalnız manuel test edilmiş.

## İlk uygulama sırası

1. Core domain modelleri.
2. Static `SourceConnector` sözleşmesi.
3. `TargetAdapter` sözleşmesi.
4. Safe payload ve test-case modeli.
5. Generic REST target adapter.
6. OpenAI-compatible target adapter.
7. Response evaluation engine.
8. Active Security Scan runner.
9. Static document Security Scan.
10. Terminal/JSON/HTML raporları.
11. OpenWebUI connector.
12. Ek platform adapter’ları.

Bir platformu yalnız import etmek “destek” sayılmaz. Capability discovery, hata davranışı, credential redaksiyonu, mock/contract fixture ve belgelenmiş sürüm olmadan Tier 1 ilan edilmez.
