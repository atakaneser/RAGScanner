# Standalone HTML report

HTML reporter embedded CSS içeren tek dosya üretir; external asset/font/CDN, analytics, network ve
JavaScript yoktur. Native keyboard-accessible `details/summary`, semantic landmarks, responsive
viewport, color-independent label ve print stylesheet kullanır.

Tüm dynamic değerler escape edilir. Source HTML/Markdown/SVG render edilmez, URL clickable yapılmaz,
PDF/DOCX gömülmez. CSP `default-src`, `script-src` ve `connect-src` değerlerini `none` yapar.

```bash
uv run ragscanner report examples/reports/sample-report-input.json \
  --format html --output examples/reports/sample-report.html
```

Fixture tamamen sentetiktir.

