# RS-007: TXT and Markdown parsers

**Objective:** Convert TXT/Markdown into safe normalized parser output with structural metadata.  
**Rationale:** Text formats provide the lowest-risk first vertical slice.  
**Dependencies:** RS-004, RS-006; RS-010 contract alignment.  
**Scope:** Encoding/BOM/newlines, headings/lists/tables/code metadata, page-not-applicable semantics, malformed/empty handling.  
**Out of scope:** Rendering Markdown HTML, executing includes, fetching links, chunking policy.  
**Implementation guidance:** Preserve source offsets where possible and literal content; use a non-rendering parser mode; surface lossy decoding.  
**Security considerations:** Never execute markup, HTML, links, or code; limit bytes/lines/nesting; sanitize diagnostics.  
**Acceptance criteria:** Fixtures parse deterministically; empty/malformed/unsupported encoding outcomes explicit; structure supports later chunk checks.  
**Tests:** Golden fixtures, mixed encodings/newlines, huge lines, embedded HTML/injection, tables/lists/code, false-positive cases.  
**Documentation changes:** Community formats and limitations.  
**Completion checklist:** [ ] Fixture corpus [ ] Limits enforced [ ] Offsets tested [ ] No rendering [ ] Docs updated

