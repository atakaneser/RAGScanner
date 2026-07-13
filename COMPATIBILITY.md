# Platform compatibility plan

This table describes planned roles, not current availability. A platform producing LLM output does
not prove retrieval. OpenWebUI is an integration rather than RAGScanner Core.

| Platform | SourceConnector | TargetAdapter | ModelProvider | Initial target tier |
|---|---:|---:|---:|---|
| Local filesystem | Yes | No | No | Tier 1 |
| Generic OpenAI-compatible | No | Yes | Yes | Tier 1 |
| OpenWebUI | Yes | Yes | Yes | Tier 1 |
| OpenAI | Vector store/File Search | Chat/Responses | Chat/Embedding | Tier 1 |
| Hugging Face TGI/Endpoint | No | Yes | Yes | Tier 1/2 |
| Ollama | No | Yes | Yes | Tier 1 |
| vLLM, LiteLLM, NVIDIA NIM | No | Yes | Yes | Tier 2 through OpenAI-compatible |
| Qdrant, Chroma | Yes | No | No | Tier 1 candidate |
| Weaviate, Pinecone, Milvus, pgvector | Yes | No | No | Tier 2 candidate |
| Custom REST/Python callback | Capability-dependent | Yes | Optional | Experimental |

## Tier definitions

- **Tier 1:** Official version matrix, CI contract fixtures, and maintainer verification.
- **Tier 2:** Expected compatibility through a generic protocol plus community fixture validation.
- **Experimental:** Unstable, incomplete, or manually tested only.

## Required order

Core models → SourceConnector contract → TargetAdapter contract → safe test model → Generic REST →
OpenAI-compatible adapter → response evaluation → active runner → static security → reports →
OpenWebUI connector → additional adapters.

An import is not support. Tier 1 requires capability discovery, documented error behavior,
credential redaction, contract fixtures, and an explicit version matrix.
