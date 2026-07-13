# Unified static scan pipeline

`StaticScanPipeline` is framework-independent orchestration:

```text
filesystem -> bounded discovery/read -> parser -> normalization -> chunking
           -> static security + duplicate + chunk quality -> scores -> report input
```

TXT, Markdown, text-based PDF, and DOCX use an explicit registry with no dynamic import. Each file
passes independent stages; a failure stops that file's later stages while other files continue.
Scanner failures become typed stage errors without automatically disabling unrelated scanners.

A direct file scan confines the root to its parent and exact filename. It is `single_source`; cross-
document checks remain not-assessed with reasons. Collections enable applicable cross-document
checks. Missing freshness/version-conflict implementations remain visibly not-assessed.

Statuses are completed, completed-with-warnings, failed, or cancelled. Findings are not operational
failures. Scores use assessed-only product formulas and do not include unimplemented retrieval,
answer, freshness, or RAG Rot dimensions. Events use a provider-neutral sink.

Exit codes: `0` success, `1` operational/report failure, `2` CLI/config error, `3` fail-on threshold,
and `130` cancellation.
