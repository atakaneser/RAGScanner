# Local dashboard

`ragscanner serve` exposes a server-rendered dashboard at `http://127.0.0.1:8000/`. It shows the
latest risk posture and assessment coverage, recent persisted scans, and durable job status.

The New scan drawer can queue a one-time or recurring local file/folder scan, or an explicitly
consented OpenWebUI knowledge base. Recurring definitions and their generated executions appear in
separate sections. Queued/running jobs may be cancelled; failed/cancelled jobs may be retried. The
machine Host Service materializes due intervals and executes the durable queue.

The dashboard is a single-user localhost surface. It never receives or embeds the API Bearer key.
Mutating forms use a strict SameSite HttpOnly CSRF cookie plus form token and call application
services directly. This is not a substitute for authentication if the service is exposed beyond
loopback.

The responsive UI includes localized timestamps and labels in six languages, persistent display and
AI defaults, date/source report filters, coverage-aware comparison, detailed expandable reports,
safe activity/error codes, and stable readable IDs. Notifications, calendar/cron schedules, and a
declared cross-browser/accessibility support matrix remain planned.

The application shell uses a persistent, icon-led navigation rail for overview, sources, scan jobs,
schedules, reports, latest findings, activity, AI settings, integrations, and general settings.
Links without an independent route target the corresponding implemented page section rather than
claiming that a planned workflow is available.

Opening Settings automatically checks the selected local AI provider and lists only models returned
by its bounded discovery endpoint. A saved model that is no longer installed is removed from the
editable form and replaced with the first verified model when available; the user must still save
the proposed change. Remote-provider discovery remains explicit and is never triggered by opening
Settings.

Dashboard-entered source credentials remain outside SQLite. When a machine-data migration preserves
the protected `secrets/` directory but invalidates an older absolute `file-secret:` path, dashboard
rendering safely rebinds the reference by validated secret identifier within the current machine
data root. It never searches arbitrary paths or copies the secret value into application state.

See [ADR-0022](decisions/0022-authenticated-local-job-control-and-dashboard.md).
