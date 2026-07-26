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

## AI output is invalid

Run `ragscanner update` before retrying so the Host Service uses the latest prompt and context
budgets. RAGScanner caps the primary advisory context at 18,000 characters and uses a separate
6,500-character recovery request after malformed output. Ollama is asked for a 16,384-token context
window. If `ai_output_invalid` remains after an update and rescan, confirm that the selected model
supports chat plus JSON output; then include the safe activity code, provider name, model name, and
timestamp in a private diagnostic report. Never attach the model response, source evidence, or API
key.

## Diagnostic information

For installed users:

```bash
ragscanner --version
ragscanner doctor
ragscanner scan "path/to/source" --verbose
```

For contributors, run the same commands with `uv run` from the repository root. Never attach API
keys, raw customer documents, private endpoints, or unredacted reports to a public issue.
