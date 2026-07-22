# ADR-0039: Local saved-report export adapters

**Status:** Accepted

## Context

The dashboard stores a bounded, redacted `ReportDocument` snapshot in SQLite but previously offered
only an interactive detail page. Users need portable HTML, Excel, and PDF files without weakening
the local-first boundary or re-reading untrusted raw source content.

## Decision

Add authenticated dashboard download routes for standalone HTML, `.xlsx`, and PDF. Delivery-only
exporters consume the already persisted `ReportDocument`; they do not import connectors, access raw
documents, or use the network.

- HTML escapes all dynamic fields, embeds its styles, contains no script, and uses a CSP that blocks
  external assets and connections.
- XLSX uses separate summary, finding, coverage, ingestion, and optional AI sheets. Text beginning
  with spreadsheet formula characters is forced to remain text.
- PDF is generated locally with ReportLab, uses packaged or standard CJK font resources, includes
  page numbers, and favors readable sequential finding sections over wide clipped tables.
- Product labels follow the selected dashboard locale. Source evidence and user-owned content stay
  in their recorded language.
- Download responses are attachments, use `no-store` and `nosniff`, and retain the existing local
  administrator boundary.

## Consequences

`openpyxl` and `reportlab` become runtime dependencies. Export generation may consume CPU and memory,
so it runs in the thread pool and remains bounded by the persisted report model. The CLI's existing
JSON and HTML reporters remain compatible and separate from the dashboard download presentation.
