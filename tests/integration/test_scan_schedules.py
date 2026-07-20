from datetime import UTC, datetime, timedelta

from ragscanner.jobs import JobStatus
from ragscanner.storage import (
    ScanScheduleRequest,
    SQLiteJobRepository,
    SQLiteScheduleRepository,
)


def test_due_schedule_creates_one_idempotent_job_and_advances(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "history.sqlite3"
    schedules = SQLiteScheduleRepository(database)
    jobs = SQLiteJobRepository(database)
    start = datetime(2026, 7, 20, 8, tzinfo=UTC)
    try:
        schedule = schedules.create(
            ScanScheduleRequest(
                name="Daily knowledge health",
                interval_minutes=60,
                payload={
                    "source_kind": "local",
                    "execution_mode": "scheduled",
                    "source_name": "Support knowledge",
                    "path": str(tmp_path / "knowledge"),
                    "ai": {"enabled": False},
                },
            ),
            now=start,
        )

        assert schedule.display_id == "RAGSCH-0001"
        assert schedules.materialize_due(jobs, now=start + timedelta(minutes=59)) == 0
        assert schedules.materialize_due(jobs, now=start + timedelta(minutes=60)) == 1
        assert schedules.materialize_due(jobs, now=start + timedelta(minutes=60)) == 0
        queued = jobs.list().items
        assert len(queued) == 1
        assert queued[0].status is JobStatus.QUEUED
        assert queued[0].payload["execution_mode"] == "scheduled"
        advanced = schedules.list()[0]
        assert advanced.next_run_at == start + timedelta(minutes=120)
    finally:
        jobs.close()
        schedules.close()
