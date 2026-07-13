# RS-038: Public website and account shell

**Objective:** Build the required accessible `ragscanner.com` public routes and authenticated app shell with truthful content.  
**Rationale:** Product education and conversion need a credible surface without overstating availability.  
**Dependencies:** RS-001; OD-017/019.  
**Scope:** Minimal documentation routes, navigation, design system/themes, product/security/privacy content, sample reports, contact/support, and optional dashboard shell.  
**Out of scope:** Scanner/dashboard feature logic, checkout (RS-040), unapproved legal text/analytics.  
**Implementation guidance:** Content-driven pages, real synthetic finding examples, performance budgets, SEO metadata, explicit available/planned labels.  
**Security considerations:** CSP/headers, XSS, form abuse/spam, session boundary, safe external links, no private URLs, minimal analytics.  
**Acceptance criteria:** All routes have reviewed content/states; WCAG target and performance budget pass; claims match status; mobile/light/dark work.  
**Tests:** Unit/E2E route smoke, accessibility, visual regression, headers, links, forms/abuse, performance.  
**Documentation changes:** Website content inventory/deployment/status.  
**Completion checklist:** [ ] Content/legal review [ ] A11y pass [ ] Security headers [ ] Performance pass [ ] Claims accurate
