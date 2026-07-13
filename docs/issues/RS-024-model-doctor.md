# RS-024: Model doctor

**Objective:** Diagnose configured chat/embedding provider connectivity and capabilities without exposing data.  
**Rationale:** BYOM failures must be distinguishable before a scan.  
**Dependencies:** RS-020, RS-022, RS-023.  
**Scope:** Configuration validation, locality/endpoint display, credentials-presence (not value), model/capability probes, dimensions/context/structured output where safe.  
**Out of scope:** Benchmarking model quality, sending customer excerpts, installing/pulling models.  
**Implementation guidance:** Use fixed synthetic prompts/text; machine-readable and human output; actionable failure categories.  
**Security considerations:** Never echo tokens/headers; SSRF controls; explicit network action; bounded probe cost; safe error redaction.  
**Acceptance criteria:** Reports each provider separately, locality and capabilities; no document access; exit codes useful; failures cannot leak credentials.  
**Tests:** Deterministic providers, network failures, malformed responses, redaction snapshots, chat/embedding mismatch, cost bounds.  
**Documentation changes:** Models, configuration, troubleshooting.  
**Completion checklist:** [ ] Synthetic only [ ] Redaction pass [ ] Exit codes [ ] Locality shown [ ] Docs updated

