# Feature catalog

Status legend: **Foundation** means documented only; every planned capability is free and is not implemented yet.

| Area | Planned capability | Edition / milestone |
|---|---|---|
| Core | Finding, scan, score, rule, provider and connector contracts | M1 |
| Inputs | Local TXT, Markdown, PDF, DOCX | M1 |
| Knowledge | Normalization, exact/near duplicates, chunk quality, freshness | M1 |
| Security | Prompt injection, encoded payload, secrets, PII and poisoning signals | M1–M2 |
| Active security | Prompt injection payloads, leakage probing, function abuse, context manipulation | M2 |
| Reports | Terminal, JSON, basic escaped HTML | M1 |
| Models | Local embeddings, semantic duplicates, BYOM, balanced analysis | M2 |
| Models | Contradiction candidates and optional verification | M2 |
| Integration | OpenWebUI discovery, synchronization, manual scans | M3 |
| Targets | Generic OpenAI-compatible, OpenAI, Hugging Face TGI, OpenWebUI, custom REST | M2–M6 |
| Sources | OpenAI vector stores, Qdrant, Chroma, Weaviate, Pinecone, Milvus, pgvector | M6+ |
| API | Authenticated scan and result contracts | M3 |
| Operations | History, comparisons, schedules, trends, notifications | M4 |
| Workflow | Acknowledge, resolve, suppress, false-positive with audit trail | M4 |
| Web | Ücretsiz yerel/self-hosted dashboard ve dokümantasyon | M4–M5 |
| Protocol | Basic MCP adapter | Future |

Detailed detector coverage remains subject to source capabilities. Static filesystem scans cannot prove retrieval relevance, tenancy, or unused content without queries, labels, configuration, or telemetry.
