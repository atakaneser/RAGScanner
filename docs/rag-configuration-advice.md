# RAG configuration advice

RAGScanner reports an evidence-informed starting configuration for the selected RAG workload. It
does not claim a universal best chunk size. Query distribution, document structure, tokenizer,
embedding model, generator context, and retrieval method can all change the optimum.

## Workload profiles

| Profile | Recommended token range | Target | Overlap | Initial top-k | Intended use |
|---|---:|---:|---:|---:|---|
| `fact_lookup` | 40–256 | 128 | 12 | 5 | Short, precise factual questions |
| `general_qa` | 50–500 | 300 | 30 | 5 | Mixed documentation and question types |
| `policy_procedure` | 80–700 | 450 | 45 | 6 | Policies, procedures, and neighboring steps |
| `long_context_research` | 120–1,024 | 700 | 70 | 8 | Broad synthesis and research questions |
| `code_assistant` | 80–1,000 | 600 | 60 | 6 | Code with structural declaration boundaries |
| `table_analytics` | 80–800 | 500 | 0 | 5 | Tables that should remain intact |

All profiles prefer structure-aware splitting, page/table/code preservation, and heading context.
Boundary quality takes priority over forcing every chunk to a numeric target. Declared embedding and
generator context limits are checked for headroom; provider metadata and prompt overhead still need
to be reserved by the operator.

Configure a scan in `ragscanner.toml`:

```toml
[rag]
profile = "policy_procedure"
embedding_context_tokens = 8192
generator_context_tokens = 32768
retrieval_top_k = 6
```

Or override it on the CLI:

```bash
ragscanner scan ./knowledge \
  --rag-profile policy_procedure \
  --embedding-context-tokens 8192 \
  --generator-context-tokens 32768 \
  --retrieval-top-k 6
```

The dashboard asks for the workload in the final job step. The saved report compares configured,
recommended, and observed values and includes the same advice in JSON, terminal verbose output,
standalone HTML, Excel, and PDF.

## Required validation

Build a representative query set with relevance labels and compare at least one smaller and one
larger candidate. Record Recall@k, nDCG@k or MRR, context precision/recall, answer faithfulness,
answer relevance, citation correctness, latency, and retrieved-token cost. Split results by source
format, language, and query type. Do not select a profile solely because its static chunk statistics
look healthy.

The starting ranges follow published retrieval and chunking evidence, including research showing
that smaller chunks often help short factual tasks, larger chunks can help broad-context tasks, and
semantic chunking does not consistently outperform simpler methods. The report embeds the exact
reference URLs used by the advisor.
