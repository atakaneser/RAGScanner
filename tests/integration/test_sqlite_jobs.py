from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from ragscanner.jobs import JobKind, JobLeaseLostError, JobRequest, JobStateError, JobStatus
from ragscanner.storage import SQLiteJobRepository


def test_enqueue_is_idempotent_and_preserves_only_secret_references(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "jobs.sqlite3"
    repository = SQLiteJobRepository(path)
    try:
        request = JobRequest(
            kind=JobKind.SCAN,
            payload={"path": "knowledge", "credential_ref": "env:SYNTHETIC_TOKEN"},
            idempotency_key="manual-scan:knowledge:001",
        )

        first = repository.enqueue(request)
        second = repository.enqueue(request)

        assert first.id == second.id
        assert first.display_id == "RAGSCN-0001"
        assert repository.list().total == 1
        assert second.payload["credential_ref"] == "env:SYNTHETIC_TOKEN"
    finally:
        repository.close()


def test_atomic_claim_assigns_each_job_to_only_one_worker(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "jobs.sqlite3"
    creator = SQLiteJobRepository(path)
    try:
        first = creator.enqueue(JobRequest(kind=JobKind.SCAN, payload={"path": "one"}))
        second = creator.enqueue(JobRequest(kind=JobKind.SCAN, payload={"path": "two"}))
    finally:
        creator.close()

    def claim(worker_id: str) -> str | None:
        repository = SQLiteJobRepository(path)
        try:
            job = repository.claim(worker_id, lease_duration=timedelta(seconds=30))
            return job.id if job else None
        finally:
            repository.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        claimed = list(executor.map(claim, ["worker-a", "worker-b"]))

    assert set(claimed) == {first.id, second.id}


def test_heartbeat_requires_live_owner_and_expired_lease_is_reclaimed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    try:
        queued = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}), now=start
        )
        first = repository.claim("worker-a", lease_duration=timedelta(seconds=5), now=start)
        assert first is not None
        assert first.id == queued.id
        assert first.attempt_count == 1

        with pytest.raises(JobLeaseLostError):
            repository.heartbeat(
                queued.id,
                "worker-b",
                lease_duration=timedelta(seconds=5),
                now=start + timedelta(seconds=1),
            )

        reclaimed = repository.claim(
            "worker-b",
            lease_duration=timedelta(seconds=5),
            now=start + timedelta(seconds=6),
        )
        assert reclaimed is not None
        assert reclaimed.id == queued.id
        assert reclaimed.lease_owner == "worker-b"
        assert reclaimed.attempt_count == 2
    finally:
        repository.close()


def test_cancellation_is_immediate_when_queued_and_cooperative_when_running(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    try:
        queued = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "queued"}), now=start
        )
        cancelled = repository.request_cancellation(queued.id, now=start)
        assert cancelled.status is JobStatus.CANCELLED

        active = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "active"}), now=start
        )
        assert (
            repository.claim("worker-a", lease_duration=timedelta(seconds=30), now=start)
            is not None
        )
        requested = repository.request_cancellation(active.id, now=start + timedelta(seconds=1))
        assert requested.status is JobStatus.CANCEL_REQUESTED
        heartbeat = repository.heartbeat(
            active.id,
            "worker-a",
            lease_duration=timedelta(seconds=30),
            now=start + timedelta(seconds=2),
        )
        assert heartbeat.status is JobStatus.CANCEL_REQUESTED

        with pytest.raises(JobStateError):
            repository.succeed(active.id, "worker-a", now=start + timedelta(seconds=3))
        final = repository.cancel(active.id, "worker-a", now=start + timedelta(seconds=3))
        assert final.status is JobStatus.CANCELLED
    finally:
        repository.close()


def test_exhausted_expired_lease_is_failed_without_another_execution(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    try:
        queued = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}, max_attempts=1),
            now=start,
        )
        repository.claim("worker-a", lease_duration=timedelta(seconds=5), now=start)

        assert (
            repository.claim(
                "worker-b",
                lease_duration=timedelta(seconds=5),
                now=start + timedelta(seconds=6),
            )
            is None
        )
        failed = repository.get(queued.id)
        assert failed is not None
        assert failed.status is JobStatus.FAILED
        assert failed.error_code == "lease_expired"
    finally:
        repository.close()


def test_failed_or_cancelled_job_can_be_manually_retried(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    start = datetime(2026, 7, 14, 12, tzinfo=UTC)
    try:
        queued = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}), now=start
        )
        cancelled = repository.request_cancellation(queued.id, now=start)
        assert cancelled.status is JobStatus.CANCELLED

        retried = repository.retry(queued.id, now=start + timedelta(seconds=1))

        assert retried.status is JobStatus.QUEUED
        assert retried.attempt_count == 0
        assert retried.completed_at is None
        assert retried.progress == 0
    finally:
        repository.close()
