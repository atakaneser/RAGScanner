# RS-047: Versioned active security payload pack

**Objective:** Define a versioned multilingual payload schema for prompt injection, leakage, function abuse, and context manipulation.
**Rationale:** Active tests must be reproducible and selectable by risk profile.
**Dependencies:** RS-004, RS-046; OD-026.
**Scope:** Payload ID/version/category, risk and non-destructive flags, prerequisites, expected signals, exclusions, references, and multilingual fixtures.
**Out of scope:** Payload transport, destructive tool calls, and fake vulnerability results.
**Implementation guidance:** JSON schema; safe profile only by default; validate custom packs.
**Security:** Payloads are never executed as local commands; destructive content requires separate design and approval.
**Acceptance:** Pack validity and uniqueness; safe/refusal fixture per payload; version provenance.
**Tests:** Schema, duplicate ID, malformed pack, multilingual boundary, and safe-profile selection.
**Documentation:** Payload contribution and safety guide.
**Checklist:** [x] Schema [x] Safe profile [x] Multilingual corpus [x] Malformed tests [x] Docs updated
