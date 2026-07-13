# ADR-0018: Runtime-neutral local container discovery

- Status: Accepted
- Date: 2026-07-14

## Decision

Guided OpenWebUI discovery may inspect bounded metadata from installed Docker, Podman, nerdctl, and
Finch CLIs only after explicit user consent. Commands use resolved executables with argument arrays,
never a shell, and have time/output bounds. Only running-container name, image, and published-port
metadata are considered. Candidate endpoints are converted to loopback only when the published bind
is loopback or wildcard; arbitrary LAN, remote, Kubernetes-context, socket, and filesystem scanning
is excluded.

A successful unauthenticated `/health` response is only a service candidate. Listing accessible
knowledge bases and linked or standalone/chat files requires a separate consent step and a user-
supplied API key that remains in memory. Responses are paginated, size-bounded, schema-checked, and
sanitized before terminal display.
Document/chunk retrieval requires the later production `SourceConnector` and another explicit data-
access consent boundary.

## Rationale

Users may run OpenWebUI under Docker Desktop, Podman, Rancher Desktop/containerd, Finch, OrbStack, or
compatible local tooling with dynamic host ports. Fixed-port probing misses valid deployments, while
Docker-only logic, unbounded port scans, automatic Kubernetes access, or direct runtime-socket access
would create portability, privilege, privacy, and SSRF risks.

## Consequences

- Compatible runtime CLIs can contribute dynamic loopback candidates without becoming Core dependencies.
- Missing, stopped, incompatible, or unauthorized runtimes fail closed and do not block local scans.
- Remote OpenWebUI endpoints remain explicit configuration work for the production connector.
- Discovery truthfully separates service health, authenticated KB metadata, and content access.
