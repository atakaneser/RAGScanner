# ADR-0031: Atomic Windows runtime generations for self-update

- Status: Accepted
- Date: 2026-07-17

## Decision

Make `ragscanner update` and `ragscanner repair` resolve the latest `main` branch of the official
GitHub repository by default. Preserve `RAGSCANNER_INSTALL_SOURCE` as an explicit deployment and
development override. The lifecycle commands invoke `uv` internally, so an administrator does not
need to run a separate package-install command.

On Windows, install every machine runtime into a unique directory below
`%ProgramFiles%\RAGScanner\generations`. Validate and atomically replace a machine-owned
`current-generation.txt` pointer only after the new launcher exists. Re-register and restart the
LocalSystem Task Scheduler task with that launcher before attempting best-effort removal of inactive
generations. Keep the legacy stable launcher path as a read fallback for existing installations.

Linux and macOS keep their stable isolated launcher path because their package replacement does not
have the same running-directory lock behavior. Their update command replaces the runtime and
restarts the existing system supervisor.

## Rationale

A running Windows console executable and its virtual environment can keep files locked. Reinstalling
over that same directory causes nondeterministic access-denied failures and can leave the service
partially updated. A generation handover makes installation failure non-destructive: the active
pointer remains on the previous working runtime until a complete replacement exists.

## Consequences

- Existing Windows installations can bootstrap into the generation layout with their normal
  `ragscanner update` command only when their command entry already contains this decision. Older
  user-profile command entries require the one-time transition documented by ADR-0032.
- A failed download or install leaves the previous active generation intact.
- The service definition always names an immutable generation launcher on Windows.
- Cleanup is best effort because the CLI process that initiated an update may still hold its old
  generation open; a later repair or update retries cleanup.
- Updates require network access to GitHub unless an explicit installation-source override is set.
