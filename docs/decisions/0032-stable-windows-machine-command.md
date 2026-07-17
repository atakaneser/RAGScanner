# ADR-0032: Stable Windows machine command ownership

- Status: Accepted
- Date: 2026-07-17
- Extends: [ADR-0031](0031-atomic-windows-runtime-generations.md)

## Decision

Install a stable `ragscanner.cmd` dispatcher below `%ProgramFiles%\RAGScanner\command` and register
that directory in the Windows machine `PATH`. The dispatcher reads `current-generation.txt` for
every invocation and executes the selected machine runtime. Installation, update, and repair
reconcile the dispatcher and PATH entry; uninstall removes both.

Do not attempt to rewrite the user-profile `uv` environment that is currently executing a lifecycle
command. Pre-ADR-0032 installations use one explicit `uvx --refresh --from ... ragscanner repair`
transition to run current code without installing another user tool. Newly opened terminals then
resolve the machine dispatcher first and require no future bootstrap command.

## Rationale

ADR-0031 prevented the machine Host Service runtime from overwriting its own locked files, but an
older installation could still resolve `ragscanner` to a stale user-profile `uv` tool. That old code
does not know about runtime generations and therefore cannot activate the fix that exists in a newer
repository revision. Command ownership must be machine-wide as well as service ownership.

## Consequences

- Future `ragscanner update` and `ragscanner repair` calls execute from the active machine runtime.
- A terminal opened before PATH registration must be reopened to inherit the machine PATH change.
- The existing user-profile tool may remain on disk but no longer wins command resolution in new
  terminals; the normal Windows uninstall flow may remove it separately.
- PATH editing is idempotent, preserves unrelated entries and their order, and requires the same
  administrator permission as machine installation.
