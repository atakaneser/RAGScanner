# RS-008: PDF parser

**Objective:** Extract bounded page-aware text/metadata from supported PDFs.  
**Rationale:** PDF is required Community functionality and a high-risk parser boundary.  
**Dependencies:** RS-004, RS-006; OD-025.  
**Scope:** PyMuPDF evaluation, per-page output, empty/encrypted/malformed/unsupported states, extraction quality signals, timeout/resource isolation.  
**Out of scope:** Full OCR, password cracking, arbitrary attachments/JavaScript, perfect table reconstruction.  
**Implementation guidance:** Parse in an isolated bounded worker; record library/version and page failures; never silently treat failure as empty.  
**Security considerations:** Size/page/object limits, parser crashes/hangs, decompression bombs, embedded files/links/scripts, sensitive temp-file cleanup.  
**Acceptance criteria:** Healthy, empty, malformed, encrypted, oversized and mixed-page fixtures yield explicit deterministic results without process compromise.  
**Tests:** Parser fixtures, fuzz/regression seeds, timeout/memory/page limits, Unicode, malformed/empty PDFs, cleanup.  
**Documentation changes:** Format support, limitations, troubleshooting, security model.  
**Completion checklist:** [ ] Isolation reviewed [ ] Malformed corpus passes [ ] Limits measured [ ] Failures visible [ ] Docs updated

