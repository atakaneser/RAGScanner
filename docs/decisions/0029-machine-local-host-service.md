# ADR-0029: Machine-local Host Service and dashboard hostname

## Status

Superseded in part by [ADR-0038](0038-fixed-localhost-address-and-password-rotation.md)

## Context

The per-user desktop Agent cannot process RAG scans when the user is signed out. This is unsuitable
for an always-on OpenWebUI Docker host. The dashboard must remain local and must not require public
DNS or an internet account.

## Decision

RAGScanner uses one visible `ragscanner install` entry point to create an elevated **Host Service**.
The Host Service is an internal runtime component, not a separate user installation choice. It runs the localhost dashboard/API and
one durable worker independently of interactive user sessions. The installer can add exactly one
marked hosts-file entry mapping `local.ragscanner.com` to `127.0.0.1`; it never modifies public DNS
or makes the dashboard reachable from another machine.

The executable runtime is installed outside user profiles (`Program Files`, `/opt`, or the
machine-level macOS Application Support directory). Persistent SQLite state is stored in
`ProgramData`, `/var/lib`, or the machine-level macOS Application Support directory. Service
temporary files use a service-owned `temp` directory; disposable interactive CLI/browser caches may
use the signed-in user's platform cache directory. Windows runs the console Host executable as a
boot-triggered Task Scheduler task under `SYSTEM`, with restart-on-failure and no execution time
limit. Its task definition is written as BOM-prefixed UTF-16LE because `schtasks.exe` does not
reliably accept a BOM-less UTF-8 task file. The principal uses the LocalSystem SID and omits the
optional XML `LogonType`; the Task Scheduler XML enumeration does not accept the `ServiceAccount`
API constant as a text value. Linux uses a system `systemd` unit and macOS uses a system
`LaunchDaemon`. Update and repair
replace the isolated runtime and restart or re-register the platform supervisor. Uninstall removes
the supervisor registration and runtime while preserving machine data unless `--purge-data` is
supplied.

The Host Service has a first-run dashboard bootstrap screen. It creates one local administrator with
an scrypt password hash and an HttpOnly, SameSite=Strict, time-limited local session. No password is
stored in reports, SQLite history, job payloads, logs, or source control.

## Consequences

`ragscanner install` requires administrator permission because it changes a machine-wide service and
the hosts file. The dashboard may guide the user, but it cannot silently elevate browser privileges.
Windows explicitly uses a boot task under `SYSTEM` because the packaged console launcher is not a
native Service Control Manager executable. Linux uses a dynamic systemd identity with
`StateDirectory`, and macOS uses a system LaunchDaemon. Filesystem access restrictions remain
deployment concerns; OpenWebUI access should use a separate non-admin service account and external
secret reference.
