# RS-046: TargetAdapter contract

**Objective:** Define vendor-neutral capabilities, requests, responses, and errors for active tests against running RAG/chat endpoints.
**Rationale:** OpenAI, TGI, OpenWebUI, and custom REST support must not create vendor branches in Core.
**Dependencies:** RS-004 core models; ADR-0011; OD-027.
**Scope:** Health checks, capability discovery, test transport, sessions/correlation, bounded responses, timeout/cancellation, and provenance.
**Out of scope:** Concrete HTTP adapters, payload corpus, and real network calls.
**Implementation guidance:** Protocol/ABC plus deterministic fake; configuration identity remains separate from source/model roles.
**Security:** Credential redaction, allowed-host metadata, and side-effect capability are mandatory.
**Acceptance:** Fake contract tests pass; no vendor import; streaming, partial, and error responses are representable.
**Tests:** Unit/property, cancellation, malformed/oversized response, and serialization fixtures.
**Documentation:** Architecture, SDK, and compatibility contract.
**Checklist:** [ ] Contract reviewed [ ] Fake adapter [ ] No network [ ] Type tests [ ] Docs updated
