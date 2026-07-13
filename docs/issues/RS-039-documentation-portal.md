# RS-039: Documentation portal

**Objective:** Publish versioned searchable documentation for the complete free product.  
**Rationale:** Installation, privacy, models, integration, reporting, and support need maintainable customer docs.  
**Dependencies:** RS-038 and feature docs from prior milestones.  
**Scope:** `/docs` routes, navigation/search, version/status banners, quickstart/install/config/BYOM/OpenWebUI/scoring/security/reporting/troubleshooting, code samples from tests.  
**Out of scope:** Inventing commands/features, public private-access instructions, full API client generation unless available.  
**Implementation guidance:** Source docs near owning repo with publication pipeline; test snippets; canonical/versioned URLs and redirects.  
**Security considerations:** No live credentials/customer data; safe Markdown/MDX components; dependency/plugin review; prevent arbitrary script embeds.  
**Acceptance criteria:** Required pages published, searchable/navigable, version/status clear, and links/snippets pass.  
**Tests:** Build/link/spell where configured, snippet tests, XSS/MDX, accessibility, version routing.  
**Documentation changes:** Portal contributor/versioning guide.  
**Completion checklist:** [ ] Source ownership [ ] Snippets tested [ ] Status banners [ ] Safe rendering [ ] Links pass
