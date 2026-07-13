# RS-003: Python scaffold

**Objective:** Create the production-quality Community Python 3.12+ project skeleton.  
**Rationale:** Establish packaging, boundaries, checks, and release metadata before features.  
**Dependencies:** RS-001, RS-002; OD-001/002/007 decisions.  
**Scope:** `pyproject`, `uv` lock, src layout, typed empty packages/composition boundary, Ruff/mypy/pytest, build metadata, basic CLI package placeholder, CI hooks.  
**Out of scope:** Parsers, scanners, persistence behavior, working scan command.  
**Implementation guidance:** Prefer one distribution with strict modules initially; pin supported Python; enforce import boundaries; minimize runtime dependencies.  
**Security considerations:** Hash/lock dependencies, no install scripts/network side effects, secret-safe test config.  
**Acceptance criteria:** Clean checkout installs/builds; checks pass; package imports on supported matrix; module boundaries are enforced; wheel/sdist contain intended files only.  
**Tests:** Build/install smoke, import test, lint, format, types, unit test, package-content inspection.  
**Documentation changes:** Community installation, contributing, status.  
**Completion checklist:** [ ] License resolved [ ] Lockfile reviewed [ ] CI green [ ] Build inspected [ ] Docs accurate
