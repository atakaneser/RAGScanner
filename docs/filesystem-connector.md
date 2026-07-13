# Local filesystem connector

`LocalFilesystemConnector` discovers `.txt`, `.md`, `.markdown`, `.pdf`, and `.docx` under one
explicit local root and returns bounded raw bytes. It never implicitly selects the home/current
directory or a filesystem/drive root. The configured root must be absolute and non-root.

## Security and limits

- Symlinks are disabled by default. When enabled, resolved targets must remain under the root.
- Path traversal, external symlinks, URL/shell/environment expansion, and non-regular files are
  rejected or skipped.
- Reads use bounded file descriptors and final-component no-follow protection where supported.
- Hidden files are skipped by default; discovery and file-size limits are mandatory.
- Content and absolute paths are not copied into errors or logs.

MIME mapping is fixed. Text encoding and binary heuristics apply only to TXT/Markdown; PDF/DOCX
bytes go directly to bounded parsers. UTF-8 and UTF-8 BOM are supported. Strict decoding is default;
fallback codecs require explicit configuration, and replacement decoding produces a warning.

Change detection is an in-process snapshot comparison, not a watcher. It compares relative path,
nanosecond mtime, size, and optionally checksum. A cursor is invalid after restart. Without checksum,
a same-size/same-time replacement may be missed; filesystem races cannot be eliminated entirely.
