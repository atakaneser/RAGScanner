# RS-006: Filesystem source connector

**Objective:** Safely enumerate local files and emit stable source records.  
**Rationale:** Local folder scanning is the first acquisition path.  
**Dependencies:** RS-003, RS-004; OD-024/025.  
**Scope:** Include/exclude rules, supported-extension discovery, symlink policy, stable relative identity, metadata/digests, skipped reasons, deterministic order.  
**Out of scope:** Archives, network shares guarantees, parsing, file watching.  
**Implementation guidance:** Separate enumeration from reads; snapshot metadata and detect changes during scan; define case sensitivity and hidden-file defaults.  
**Security considerations:** Prevent root escape/symlink traversal, special-device reads, unbounded trees, TOCTOU surprises, and secret path logging.  
**Acceptance criteria:** Only in-root regular allowed files emitted; all skips explained; ordering/identity stable; limits configurable.  
**Tests:** Symlink loops/escape, permission errors, Unicode/case, deep trees, changing/deleted files, limits, false exclusions.  
**Documentation changes:** Configuration, supported sources, troubleshooting.  
**Completion checklist:** [ ] Threat cases pass [ ] Identity approved [ ] Limits documented [ ] No raw content logs [ ] Tests green

