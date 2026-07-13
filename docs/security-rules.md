# Security rules

İlk versioned active payload/test-case library ve ilk deterministic static rule pack uygulanmıştır.
Static JSON formatı, matcher sınırları, false-positive/context davranışı ve katkı kuralları
[`static-security-scanner.md`](static-security-scanner.md) içinde tanımlıdır. Active JSON formatı, safe-mode politikası,
kontroller, placeholder allowlist'i ve katkı kuralları
[`active-security-test-library.md`](active-security-test-library.md) içinde tanımlıdır. Bu
library static document rule engine'den ayrıdır; active testleri yalnız veri olarak tarif eder ve
hiçbir payload çalıştırmaz. Static scanner da detected/decoded içeriği çalıştırmaz.

İlk static paket prompt injection, system-prompt extraction, tool/command instruction, bounded
encoded content, invisible/hidden content, metadata poisoning, suspicious URL, secret ve optional
PII göstergelerini kapsar. Tenant retrieval ve semantic riskler bu paketin kapsamında değildir.

Each rule has a stable ID/version, category, description, supported sources, deterministic/optional-model phase, severity, confidence method, evidence redaction, remediation, references, tests, and known false positives. Severity expresses impact; confidence expresses evidence strength and must be displayed separately. Rules do not execute decoded content, fetch arbitrary URLs by default, or trust model classifications. Rule packs require signature/update/rollback and licensing decisions.
