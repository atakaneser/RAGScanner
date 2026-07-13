# RS-010: Deterministic normalization

**Objective:** Define reversible-enough canonical text forms for hashing and similarity without destroying evidence.  
**Rationale:** Duplicate/fingerprint stability depends on explicit normalization.  
**Dependencies:** RS-004, RS-007–009 interfaces.  
**Scope:** Unicode form, newline/whitespace, optional case/punctuation policies, repeated layout artifacts, language-safe profiles, versioning and source offset mapping.  
**Out of scope:** Translation, semantic rewriting, lossy mutation of report evidence.  
**Implementation guidance:** Retain original extracted text separately; compose small named transforms; fingerprint includes normalization version.  
**Security considerations:** Preserve invisible/encoded content for security rules; defend regex complexity; avoid confusable normalization hiding attacks.  
**Acceptance criteria:** Same profile is deterministic/idempotent; changes are versioned; multilingual and security-significant text is not silently erased.  
**Tests:** Property/idempotence, Unicode/confusables, whitespace/newlines, multilingual, tables/lists, invisible content and golden vectors.  
**Documentation changes:** Configuration and algorithm/version notes.  
**Completion checklist:** [x] Conservative profile approved [x] Segment offset strategy [x] Golden vectors [x] Security cases [x] Docs updated
