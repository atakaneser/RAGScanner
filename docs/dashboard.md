# Local dashboard

`ragscanner serve` exposes a server-rendered dashboard at `http://127.0.0.1:8000/`. It shows the
latest risk posture and assessment coverage, recent persisted scans, and durable job status.

The New scan drawer can queue a permitted local file/folder or an explicitly consented OpenWebUI
knowledge base. Queued/running jobs may be cancelled; failed/cancelled jobs may be retried. A
separate `ragscanner worker` process executes the queue against the same database.

The dashboard is a single-user localhost surface. It never receives or embeds the API Bearer key.
Mutating forms use a strict SameSite HttpOnly CSRF cookie plus form token and call application
services directly. This is not a substitute for authentication if the service is exposed beyond
loopback.

The initial UI is responsive and has been exercised in desktop and mobile browser viewports. Scan
detail, report comparison, connector settings, schedules, notifications, and a declared
cross-browser/accessibility support matrix remain planned.

See [ADR-0022](decisions/0022-authenticated-local-job-control-and-dashboard.md).
