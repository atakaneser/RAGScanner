# ADR-0028: Per-user local Agent for dashboard delivery

## Status

Accepted

## Context

Starting a web server and a separate worker manually makes a local dashboard feel unreliable and
prevents durable jobs from being processed while the terminal is closed. The first release remains
single-user and localhost-only; it must not require administrator access or turn into a network
service by default.

## Decision

RAGScanner provides a per-user **Local Agent**. It runs the localhost dashboard/API and one durable
worker in a single process. `ragscanner agent install` registers it for the signed-in user:

- Windows: a least-privilege logon Scheduled Task.
- macOS: a LaunchAgent in `~/Library/LaunchAgents`.
- Linux: a systemd user service in `~/.config/systemd/user`.

The Agent listens only on `127.0.0.1`. The dashboard remains a web UI, but users no longer need to
start it manually. Core, connectors, and storage ports remain independent of Agent code.

`ragscanner uninstall` removes the Agent registration and tool but preserves reports/history by
default. `--purge-data` is an explicit separate destructive action.

## Consequences

The Agent processes already-authorized queued work automatically. Source schedules and filesystem
change watches are separate follow-up work; the Agent is their host, not a claim that they already
exist. A future machine-wide service is reserved for managed deployments with a deliberate
service-account and credential-store design.
