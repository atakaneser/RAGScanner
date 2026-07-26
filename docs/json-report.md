# JSON report

The JSON report currently uses `schema_version=1.6.0` and an independent `reporter_version`. It is
UTF-8, uses stable key/item ordering, and emits timezone-aware ISO 8601 datetimes. Unavailable score
fields remain explicit `null` values. Schema 1.6 records the report language, bounded duplicate
matching content, affected-chunk/group counts, and version 2 structured advisory AI sections.
`ai_analysis_error_code` diagnoses advisory provider failures without exposing raw exceptions or
response bodies. Deterministic findings and scores remain complete when AI analysis is unavailable.
If the primary structured model output is invalid, the compact retry requests plain text.
RAGScanner wraps usable text into the same schema with empty structured sections and a localized
`limitations` entry. Unusable or wrong-language retry text is replaced by verified localized report
facts, so provider output formatting alone does not create a terminal `ai_output_invalid`.

Schema: [`ragscanner-report-v1.schema.json`](../schemas/report/ragscanner-report-v1.schema.json).
A breaking change requires a new major schema version. If the configured byte limit is exceeded,
the reporter fails explicitly instead of writing invalid or truncated JSON.
