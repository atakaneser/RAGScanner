# Local dashboard

`ragscanner serve` exposes a server-rendered dashboard only at `http://localhost:8765/`; the socket
binds to `127.0.0.1` and the port is intentionally fixed. It shows the
latest risk posture and assessment coverage, recent persisted scans, and durable job status.

The New scan drawer can queue a one-time or recurring local file/folder scan, an explicitly
consented OpenWebUI knowledge base, or a website source. Website sources accept one page, a supported
document, a same-origin sitemap, or an accessible SharePoint URL. Optional authenticated web access
uses an external bearer-token environment reference; jobs and reports never contain the token.
Website requests require HTTPS outside loopback, do not execute scripts, reject redirects and
cross-origin sitemap entries, and enforce page and byte limits. Recurring definitions and their
generated executions appear separately. Queued/running jobs may be cancelled; failed/cancelled jobs
may be retried. The machine Host Service materializes due intervals and executes the durable queue.

The dashboard is a single-user localhost surface. It never receives or embeds the API Bearer key.
Mutating forms use a strict SameSite HttpOnly CSRF cookie plus form token and call application
services directly. This is not a substitute for authentication if the service is exposed beyond
loopback.

The Settings page changes the local administrator password after verifying the current password.
Passwords require at least 14 characters, remain stored only as an scrypt hash, and changing one
rotates the session secret so every other signed-in dashboard session is closed.

The responsive UI includes localized timestamps and labels in six languages, persistent display and
AI defaults, date/source report filters, coverage-aware comparison, detailed expandable reports,
safe activity/error codes, and stable readable IDs. Notifications, calendar/cron schedules, and a
declared cross-browser/accessibility support matrix remain planned.

Saved reports can be permanently deleted from the report table or detail page after confirmation.
Overview health and history immediately recalculate from the latest remaining report.

The application shell uses a persistent, icon-led navigation rail for overview, sources, scan jobs,
schedules, reports, latest findings, activity, AI settings, integrations, and general settings.
Links without an independent route target the corresponding implemented page section rather than
claiming that a planned workflow is available.

Opening Settings automatically checks the selected local AI provider and lists only models returned
by its bounded discovery endpoint. A saved model that is no longer installed is removed from the
editable form and replaced with the first verified model when available; the user must still save
the proposed change. Remote-provider discovery remains explicit and is never triggered by opening
Settings.

AI adapters first request structured JSON. When an older Ollama or OpenAI-compatible server rejects
that optional parameter with HTTP 400, RAGScanner retries once in prompt-only JSON compatibility
mode and still validates the response schema. If both requests fail, the report records
`ai_provider_request_invalid` with endpoint/model guidance.

Dashboard-entered source credentials remain outside SQLite. When a machine-data migration preserves
the protected `secrets/` directory but invalidates an older absolute `file-secret:` path, dashboard
rendering safely rebinds the reference by validated secret identifier within the current machine
data root. It never searches arbitrary paths or copies the secret value into application state.

See [ADR-0022](decisions/0022-authenticated-local-job-control-and-dashboard.md).
