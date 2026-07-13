# Static RAG security scanner

The static scanner inspects documents, normalized text, chunks, metadata, parser warnings, and
normalization annotations locally and deterministically. It neither proves application behavior nor
replaces authorized active testing. It executes/renders nothing, follows no URL, and performs no
network/subprocess call. Encoded inspection is strictly bounded and never executed.

The initial versioned JSON packs cover prompt injection, system-prompt extraction, tool abuse,
suspicious commands, encoded payloads, hidden content, secrets, optional PII, suspicious URLs, and
metadata poisoning. Multilingual indicators are supported. PII is disabled by default and a pattern
match is not proof of identity.

Severity expresses impact; confidence expresses evidence strength. Documentation, quoted examples,
canaries, no-op text, and explicit refusal context reduce confidence/classification rather than
hiding evidence. Static matching never confirms that a running target followed an instruction.

Evidence is bounded, escaped, secret-masked, and mapped to page/line/chunk where possible. Rule
provenance records pack/rule/matcher/range and confirms that decoded content was not executed and
URLs were not fetched.

Rules use restricted exact, substring, bounded regex, token, metadata, annotation, warning,
decoded-content, entropy, URL, secret, and PII matchers. Arbitrary code/templates are impossible and
risky regex constructs fail loading. New rules require TP, FP, boundary, multilingual, and limit
fixtures plus a version bump when semantics change.

`ragscanner security scan` supports local TXT/Markdown/PDF/DOCX and terminal/JSON output only.
Heuristics can miss or over-report risk; not-detected is never a guarantee.
