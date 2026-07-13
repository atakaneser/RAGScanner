# Feature catalog

All capabilities are free. Current implementation status is documented in
[`docs/status/current.md`](docs/status/current.md); milestone labels below are planning groupings,
not availability claims.

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
| Integration | OpenWebUI discovery and manual knowledge-content scans; synchronization planned | M3 |
| Targets | Generic OpenAI-compatible, OpenAI, Hugging Face TGI, OpenWebUI, custom REST | M2–M6 |
| Sources | OpenAI vector stores, Qdrant, Chroma, Weaviate, Pinecone, Milvus, pgvector | M6+ |
| API | Local history plus authenticated asynchronous scan/job contracts | M3 |
| Operations | History, comparisons, schedules, trends, notifications | M4 |
| Workflow | Acknowledge, resolve, suppress, false-positive with audit trail | M4 |
| Web | Initial free local dashboard; detail/settings/schedules planned | M4–M5 |
| Protocol | Basic MCP adapter | Future |

Detailed detector coverage remains subject to source capabilities. Static filesystem scans cannot prove retrieval relevance, tenancy, or unused content without queries, labels, configuration, or telemetry.
