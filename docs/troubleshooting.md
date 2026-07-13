# Troubleshooting

## Command not found

Confirm the one-time installation and tool directory:

```bash
uv tool list
uv tool update-shell
```

Restart the terminal after `uv tool update-shell`, then run `ragscanner doctor`.

If the command exists but its environment is damaged, run `ragscanner repair`. To retrieve the
latest version from the original installation source, run `ragscanner update`.

## A path is rejected

- Put the complete path in quotes when it contains spaces or parentheses.
- Use `C:\...` paths in Windows PowerShell, not in a Linux container shell.
- Use `/app/...` paths only inside the container or Linux environment where they exist.
- Confirm that the current user can read the file and its parent folder.
- Supported inputs are TXT, Markdown, PDF, and DOCX.

## A PDF cannot be parsed

The error category distinguishes malformed, encrypted, zero-page, image-only/OCR-needed, limit,
timeout, and parser failures. Follow the remediation shown in the terminal or HTML ingestion table.
RAGScanner does not silently repair or rewrite the source PDF.

## Diagnostic information

For installed users:

```bash
ragscanner --version
ragscanner doctor
ragscanner scan "path/to/source" --verbose
```

For contributors, run the same commands with `uv run` from the repository root. Never attach API
keys, raw customer documents, private endpoints, or unredacted reports to a public issue.
