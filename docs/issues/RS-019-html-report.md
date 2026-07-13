# RS-019: Safe basic HTML report

**Objective:** Generate a self-contained accessible Community HTML report from the report contract.  
**Rationale:** Users need a shareable human report without a dashboard.  
**Dependencies:** RS-018.  
**Scope:** Jinja template, summary/categories/findings/provenance/limitations, print styles, navigation/filtering only if safe without external services.  
**Out of scope:** Server, active untrusted scripts, remote assets, trends/comparisons, and PDF in this issue.  
**Implementation guidance:** Escape by default, strong CSP-compatible output, no remote fonts/analytics; render report DTO only.  
**Security considerations:** Test XSS via filenames, source text, URLs, model output; safe links, no inline raw HTML, secret/content minimization.  
**Acceptance criteria:** Opens offline; all untrusted fixtures display as text; required fields/failed checks visible; keyboard/print usability reviewed.  
**Tests:** Golden DOM, XSS corpus, CSP, large findings, accessibility smoke, no-network asset check.  
**Documentation changes:** Reporting and usage.  
**Completion checklist:** [ ] XSS tests [ ] Offline verified [ ] Accessibility smoke [ ] No remote assets [ ] Docs updated
