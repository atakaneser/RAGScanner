# Configuration

Unified scans accept local TOML only. There is no arbitrary code, dynamic import, environment
interpolation, or secret field. Unknown fields are rejected.

```text
defaults < TOML configuration < explicit CLI options
```

Configuration groups cover discovery/file limits, static security selection, chunking, duplicate
and quality analysis, parser/normalization limits, and report format/path/overwrite policy. See
`ragscanner scan --help` for CLI overrides.

```toml
[scan]
recursive = true
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

[report]
format = "html"
output = "ragscanner-report.html"
show_relative_paths = true
max_findings = 500
overwrite = false
create_parent_directories = false
```

Overwrite is disabled by default. Missing parent directories are created only after explicit
configuration. Reports use a temporary file and atomic replacement in the destination directory.
