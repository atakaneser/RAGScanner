# JSON report

The JSON report currently uses `schema_version=1.2.0` and an independent `reporter_version`. It is
UTF-8, uses stable key/item ordering, and emits timezone-aware ISO 8601 datetimes. Unavailable score
fields remain explicit `null` values. Schema 1.1 adds bounded per-file ingestion issues without
changing the major contract. Schema 1.2 adds the optional `ai_analysis_error_code` field so an
advisory provider failure can be diagnosed without exposing raw exceptions or response bodies.

Schema: [`ragscanner-report-v1.schema.json`](../schemas/report/ragscanner-report-v1.schema.json).
A breaking change requires a new major schema version. If the configured byte limit is exceeded,
the reporter fails explicitly instead of writing invalid or truncated JSON.
