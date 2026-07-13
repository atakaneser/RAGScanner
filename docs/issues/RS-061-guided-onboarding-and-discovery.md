# RS-061: Guided onboarding and source discovery

**Objective:** Guide normal users from a bare `ragscanner` command to safe source selection and a
first scan.  
**Rationale:** Users should not need prior knowledge of CLI syntax, installation topology, or RAG
storage paths.  
**Dependencies:** RS-005, RS-059, ADR-0016.  
**Scope:** English interactive flow, bounded local candidate discovery, consent-based loopback
service probing, connector capability/status display, and direct local scans.  
**Out of scope:** Remote content retrieval before connector implementation, whole-disk crawling,
credential persistence, scheduling, and dashboard implementation.  
**Security considerations:** Explicit consent, no redirects, loopback allowlist, short timeouts,
metadata-only discovery, and no secret/content logging.  
**Acceptance criteria:** The bare command guides the user; local scans work; OpenWebUI probing never
runs without consent; planned connectors are not presented as available; explicit subcommands
remain backward compatible; generated output is English while input remains multilingual.  
**Tests:** CLI prompts, Unicode/path handling, consent gate, bounded discovery, network destination,
English-output checks, and existing CLI regression tests.  
**Documentation changes:** README, CLI, roadmap, current status, and ADR.  
**Completion checklist:** [ ] UX reviewed [ ] Consent tested [ ] Cross-platform paths [ ] Docs
updated [ ] Full quality gates
