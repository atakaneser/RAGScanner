# Standalone HTML report

The HTML reporter creates one self-contained file with embedded CSS. It uses no external assets,
fonts, CDN, analytics, network requests, or JavaScript. Native keyboard-accessible
`details`/`summary`, semantic landmarks, a responsive viewport, color-independent labels, and a
print stylesheet are included.

The first view shows scan outcome, discovered/processed/skipped counts, assessment coverage, and a
file-ingestion remediation table. Technical identifiers and configuration are kept in a collapsed
technical-details section. Product-defined scores are scoped to assessed checks and are never
presented as a security guarantee.

Every dynamic value is escaped. Source HTML, Markdown, and SVG are never rendered; URLs are not made
clickable; PDF and DOCX files are not embedded. The CSP sets `default-src`, `script-src`, and
`connect-src` to `none`.

```bash
ragscanner report examples/reports/sample-report-input.json \
  --format html --output examples/reports/sample-report.html
```

The bundled fixture is entirely synthetic.
