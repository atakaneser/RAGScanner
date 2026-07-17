# ADR-0033: Dashboard source secrets remain process-memory only

## Status

Accepted

## Context

The dashboard previously accepted only an `env:VARIABLE_NAME` reference for an OpenWebUI API key.
Source profiles that were discovered without that reference appeared as `connection_required`, but
the scan-job source selector disabled them and offered no path to complete the connection. This was
secure but unusable, especially during first-run setup.

Persisting a raw key in SQLite or a durable job payload would violate the existing secret boundary.
A cross-platform machine secret-store abstraction is not yet available, and the machine service
must continue to support Windows SYSTEM, Linux systemd, and macOS LaunchDaemon execution.

## Decision

The dashboard accepts a raw API key as the default interactive connection method and immediately
maps it to a generated `env:RAGSCANNER_SOURCE_<PROFILE_ID>_API_KEY` reference. The value is placed
only in the running Host Service process environment. SQLite source profiles and durable jobs store
only the generated reference. The API key is never echoed in a response or rendered back into HTML.

An advanced field continues to accept an administrator-provisioned `env:` reference for unattended
operation across service restarts. Effective source capability is calculated when the dashboard is
rendered: an OpenWebUI profile is `scan_ready` only when its reference resolves in the current Host
Service; otherwise it returns to `connection_required` and the inline completion form is shown.

Only connectors with implemented content access can become scan-ready. Detected vector databases,
Kubernetes services, generic REST endpoints, and custom environments remain `metadata_only` until
their connector acceptance criteria pass.

## Consequences

- Interactive setup and job creation no longer dead-end on `connection_required`.
- A service restart intentionally forgets dashboard-pasted API keys and asks for them again.
- Administrators who need unattended recurring scans must provision an environment variable.
- A future operating-system-backed machine secret store can replace the in-memory implementation
  behind the same reference boundary without changing job payloads.
