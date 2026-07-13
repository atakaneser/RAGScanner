# RS-054: Hugging Face TGI target adapter

**Objective:** Verify TGI/OpenAI Messages compatibility with capability fixtures and adapt proven TGI differences.
**Rationale:** Importing `transformers` alone is not Hugging Face support.
**Dependencies:** RS-053.
**Scope:** TGI version/capability, model/endpoint configuration, response mapping, and official fixture documentation.
**Out of scope:** Model downloads, arbitrary `trust_remote_code`, and treating Hugging Face as a document source.
**Implementation guidance:** Reuse the generic adapter and add only verified differences.
**Security:** Token redaction, endpoint privacy, and remote-code/model supply-chain warnings.
**Acceptance:** Mock TGI fixtures pass; supported versions/modes are explicit; fallback is never silent.
**Tests:** Chat success, unsupported schema, auth, timeout, streaming, and version capability.
**Documentation:** Hugging Face target/model distinction.
**Checklist:** [ ] Official schema fixture [ ] Version matrix [ ] No remote code [ ] Tests [ ] Docs updated
