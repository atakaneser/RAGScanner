# Quality calibration

Static rule presence is not proof of detector quality. RAGScanner provides a local labelled-corpus
runner that reports precision, recall, F1, false-positive rate, Wilson 95% intervals, and slices by
rule, language, and format.

```bash
ragscanner quality calibrate ./calibration/manifest.json
ragscanner quality calibrate ./calibration/manifest.json --format json
ragscanner quality calibrate ./calibration/manifest.json \
  --minimum-precision 0.95 --minimum-recall 0.90
```

The threshold form exits with code `3` when the aggregate metric is unavailable or below the stated
minimum, which makes it suitable for CI. Calibration files are read locally, paths are confined to
the declared corpus root, and source content is not persisted.

Manifest example:

```json
{
  "schema_version": "1.0.0",
  "corpus_name": "security-regression-v1",
  "root": "cases",
  "cases": [
    {
      "id": "injection-en-001",
      "path": "injection-en-001.md",
      "language": "en",
      "format": "markdown",
      "expected_rule_ids": ["STATIC-PI-001"]
    }
  ]
}
```

The repository smoke corpus contains positive and negative prompt-injection cases for English,
Turkish, German, French, Simplified Chinese, and Italian across text, Markdown, HTML, and JSON. It is
a regression fixture, not a statistically representative production benchmark. Production
calibration needs independently reviewed labels, realistic benign near-misses, attack variations,
enough cases for meaningful confidence intervals, and held-out cases that rule authors did not tune
against.
