# RS-020: Local embedding provider

**Objective:** Add an optional offline embedding provider with reproducible model configuration.  
**Rationale:** Semantic checks should work without remote APIs.  
**Dependencies:** RS-003/004/010; OD-013.  
**Scope:** Provider capability contract, sentence-transformers adapter, model/cache/device/batch config, pre-provisioned offline mode, provenance and doctor hooks.  
**Out of scope:** Automatic remote model downloads in offline runs, chat analysis, model fine-tuning.  
**Implementation guidance:** Lazy optional dependency; explicit download/install step; normalize/vector dimensions/version and deterministic settings documented.  
**Security considerations:** Model supply-chain/checksums, cache permissions, resource exhaustion, unsafe model code, no arbitrary remote code.  
**Acceptance criteria:** Preloaded model embeds offline; missing model fails actionably without network; provenance/dimension/capabilities recorded.  
**Tests:** Fake provider contracts, offline network-denial, known vector shape, batching/cancellation/resource boundaries, model-cache errors.  
**Documentation changes:** Models, installation, privacy, troubleshooting.  
**Completion checklist:** [ ] Offline proof [ ] Supply-chain review [ ] Optional install [ ] Contract tests [ ] Docs updated

