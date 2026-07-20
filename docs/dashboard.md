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

See [ADR-0022](decisions/0022-authenticated-local-job-control-and-dashboard.md).
