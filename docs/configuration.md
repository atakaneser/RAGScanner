# Yapılandırma

Unified scan yalnız yerel TOML kabul eder. Arbitrary code, dynamic import, environment interpolation
veya secret alanı yoktur. Bilinmeyen alanlar reddedilir. Precedence:

```text
defaults < TOML config < explicit CLI options
```

```toml
[scan]
recursive = true
include = ["**/*.pdf", "**/*.docx", "**/*.md", "**/*.txt"]
exclude = ["**/archive/**"]
max_file_size_mb = 25
max_files = 10000

[security]
enabled = true
include_pii = false
minimum_severity = "low"

[chunking]
strategy = "structure_aware"
target_tokens = 500
max_tokens = 800
min_tokens = 50
overlap_tokens = 50

[duplicates]
exact = true
near = true
similarity_threshold = 0.88

[quality]
enabled = true

[limits]
pdf_max_pages = 1000
pdf_max_characters = 5000000
docx_max_characters = 5000000
normalized_max_characters = 5000000
max_chunks_per_document = 10000

[report]
format = "html"
output = "ragscanner-report.html"
show_relative_paths = true
max_findings = 500
overwrite = false
create_parent_directories = false
```

Output overwrite varsayılan kapalıdır. Eksik parent yalnız config açıkça izin verirse oluşturulur.
Report aynı dizinde temporary file + atomic replace ile yazılır.
