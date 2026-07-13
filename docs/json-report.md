# JSON report

JSON rapor `schema_version=1.0.0` ve ayrı `reporter_version` taşır. UTF-8, stable key/item ordering
ve timezone-aware ISO 8601 datetime kullanır. Unavailable score alanları explicit `null` kalır.

Şema: [`ragscanner-report-v1.schema.json`](../schemas/report/ragscanner-report-v1.schema.json).
Major kırılmada yeni schema version gerekir. Maksimum byte boyutu aşılırsa invalid/truncated JSON
yazmak yerine açık hata oluşur.

