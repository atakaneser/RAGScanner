# RS-009: DOCX parser

**Objective:** Extract ordered paragraphs, headings, lists, tables, headers/footers and metadata from DOCX safely.  
**Rationale:** DOCX is a required Community source with ZIP/XML attack risks and complex structure.  
**Dependencies:** RS-004, RS-006; OD-025.  
**Scope:** `python-docx` evaluation, structural output, repeated header/footer signals, empty/malformed/encrypted/unsupported handling.  
**Out of scope:** Macros execution, tracked-change fidelity, embedded object extraction, pixel-perfect layout.  
**Implementation guidance:** Inspect archive metadata before parse; define content ordering and tables/list boundaries; make loss visible.  
**Security considerations:** ZIP bomb/path traversal/entity expansion, external relationships, macros/OLE, temp cleanup, byte/entry/depth/time limits.  
**Acceptance criteria:** Required fixtures parse deterministically; malicious/malformed packages are rejected safely; structural locations enable findings.  
**Tests:** Healthy/empty/malformed, archive bomb simulations, external links, tables/lists/headers, Unicode, timeout/cleanup.  
**Documentation changes:** Format support/limitations and troubleshooting.  
**Completion checklist:** [x] Archive preflight [x] External content disabled [x] Fixtures pass [x] Loss documented [x] Security review
