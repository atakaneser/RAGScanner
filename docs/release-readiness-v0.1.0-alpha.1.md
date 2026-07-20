# v0.1.0-alpha.1 readiness record

## Verdict

**Repository publication is approved; tag/package release still requires a reviewed clean commit
and final release verification.** The local static product is an alpha candidate after all
automated gates pass.

## Release blockers

- The alpha package/tag may be published only after a reviewed clean baseline and final release
  verification.

## Resolved approvals

- Repository owner approved Apache-2.0; `LICENSE` and package metadata match.
- Canonical repository is `https://github.com/atakaneser/RAGScanner`.
- Private vulnerability reports use GitHub Security Advisories; public issues must not contain
  secrets, exploits or customer content.

## Fixed during readiness work

- Single-file and small multi-file knowledge bases have explicit assessment coverage.
- Wheel bundles static rules and report schema instead of assuming repository layout.
- PEP 440 alpha version comes from one source file.
- Package/wheel-smoke CI, Dependabot, security-rule issue template and non-publishing release build
  workflow were added.
- Placeholder paid-tier and unresolved CODEOWNERS entries were removed.

## Accepted alpha limitations

- Unified CLI exposes static/offline scan only.
- Scores are partial and product-defined; retrieval, answer reliability, freshness and RAG Rot may
  be `not assessed`.
- No OCR, dashboard, scheduler, OpenWebUI content connector, embeddings, or model calls. Local
  persistence is opt-in and limited to report history/comparison.
- The packaged API is read-only and loopback-only; authenticated scan/job control is not available.
- Native parser calls have cooperative rather than process-level timeout preemption.
- Lexical/heuristic detectors can produce false positives and false negatives.

There is no previous public release. The initial packaged persistence revision is
`0001_scan_history`; the current report schema is `1.2.0`.

## Local performance smoke record

Environment: Apple M1 Pro, arm64, macOS 26.5.1, Python 3.12.13. Measurements are approximate and
not universal benchmarks.

| Synthetic corpus | Result | Wall time | Peak RSS |
|---|---:|---:|---:|
| 10 small TXT | 10 docs, 10 findings, 15,889-byte JSON | 0.84 s | ~88 MiB |
| 100 small TXT | 100 docs, 100 findings, 122,446-byte JSON | 1.47 s | ~100 MiB |
| 20-page PDF | 1 doc, 20 chunks, 21 findings | 0.66 s | ~92 MiB |
| 300-paragraph DOCX | 1 doc, 33 chunks, 120 findings | 12.87 s | ~182 MiB |

The DOCX case is acceptable for alpha bounds but is a future profiling/optimization target. Limits
remain configurable; these numbers do not promise production throughput.

## Verification evidence

- Python 3.12 full suite: 317 passed.
- Python 3.13 isolated full suite: passed.
- `pip-audit`: no known dependency vulnerabilities.
- `zizmor`: no workflow findings after action pinning, checkout credential and cooldown hardening.
- Secret/privacy search hits were inert synthetic fixtures; generated reports contained no absolute
  user path, raw private key, authorization value or synthetic secret value.
- False-positive corpus passed for quoted injection, ordinary shell/PowerShell/SQL docs, placeholder
  keys, image-like Base64, localhost documentation and PII-disabled email examples. No threshold
  change was justified.
- Healthy, vulnerable, malformed and Turkish/English CLI corpora had expected status/findings.
- JSON samples validate against report schema v1; standalone HTML has CSP and no external assets.
- Wheel/sdist build passed; wheel contains 10 static rule files and the report schema. A fresh Python
  3.12 environment installed it and completed a single-source scan.

## Security review classification

- **Confirmed and fixed:** repository-relative rules broke installed-wheel scans; rules/schema are
  bundled. Workflow actions were not all commit-pinned; now hardened. Security-only coverage
  mislabeled disabled duplicate checks; now `not_assessed`.
- **Probable risks accepted for alpha:** native parser timeout preemption, filesystem TOCTOU,
  heuristic false negatives/positives and bounded in-memory large-document processing.
- **Hardening recommendations:** profile the large DOCX path, add parser subprocess isolation,
  add SBOM/provenance before a stable release.
