# RS-023: Ollama provider configuration

**Objective:** Provide a safe local Ollama setup path through common provider contracts.  
**Rationale:** Ollama is a likely BYOM route for local chat/embeddings.  
**Dependencies:** RS-020, RS-022/provider contracts, RS-024.  
**Scope:** Local endpoint/model config, capabilities, setup validation, explicit remote-host warning, provenance and examples.  
**Out of scope:** Installing/managing Ollama daemon, automatic model pulls, vendor-specific core imports.  
**Implementation guidance:** Adapter maps to neutral contracts; defaults only to loopback; model pull remains explicit user action.  
**Security considerations:** Treat non-loopback as remote consent; SSRF/TLS and unauthenticated endpoint warnings; never expose prompts in diagnostic logs.  
**Acceptance criteria:** Local stub/live-optional path works; missing daemon/model is actionable; remote address is clearly classified and consented.  
**Tests:** Stub contract, loopback classification, missing model/daemon, timeouts, redaction and malformed output.  
**Documentation changes:** Models/BYOM setup and troubleshooting.  
**Completion checklist:** [ ] Local default [ ] No auto-pull [ ] Remote warning [ ] Tests green [ ] Docs updated

