from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from ragscanner.application import DurableWorker
from ragscanner.jobs import JobKind, JobRecord, JobRequest, JobStatus
from ragscanner.storage import SQLiteJobRepository


class SuccessfulHandler:
    def execute(self, job: JobRecord, checkpoint: Callable[[float | None], JobRecord]) -> str:
        assert job.kind is JobKind.SCAN
        checkpoint(0.5)
        return "history:synthetic-result"


class FailingHandler:
    def execute(self, job: JobRecord, checkpoint: Callable[[float | None], JobRecord]) -> None:
        raise RuntimeError("synthetic sensitive detail")


def test_worker_executes_handler_and_persists_result(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    try:
        queued = repository.enqueue(JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}))
        worker = DurableWorker(
            repository,
            {JobKind.SCAN: SuccessfulHandler()},
            worker_id="worker-1",
        )

        completed = worker.run_once()

        assert completed is not None
        assert completed.id == queued.id
        assert completed.status is JobStatus.SUCCEEDED
        assert completed.progress == 1
        assert completed.result_ref == "history:synthetic-result"
    finally:
        repository.close()


def test_worker_requeues_safely_then_fails_at_attempt_limit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    try:
        queued = repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}, max_attempts=1)
        )
        worker = DurableWorker(
            repository,
            {JobKind.SCAN: FailingHandler()},
            worker_id="worker-1",
        )

        failed = worker.run_once()

        assert failed is not None
        assert failed.id == queued.id
        assert failed.status is JobStatus.FAILED
        assert failed.error_code == "job_execution_failed"
        assert "synthetic sensitive detail" not in (failed.error_message or "")
    finally:
        repository.close()


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (FileNotFoundError("sensitive path"), "source_path_not_found"),
        (PermissionError("sensitive path"), "source_permission_denied"),
        (ValueError("sensitive configuration"), "job_configuration_invalid"),
    ],
)
def test_worker_classifies_safe_actionable_failures(tmp_path, failure, code) -> None:  # type: ignore[no-untyped-def]
    class ClassifiedFailureHandler:
        def execute(self, job: JobRecord, checkpoint: Callable[[float | None], JobRecord]) -> None:
            del job, checkpoint
            raise failure

    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    try:
        repository.enqueue(
            JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}, max_attempts=1)
        )
        failed = DurableWorker(
            repository,
            {JobKind.SCAN: ClassifiedFailureHandler()},
            worker_id="worker-1",
        ).run_once()

        assert failed is not None
        assert failed.error_code == code
        assert "sensitive" not in (failed.error_message or "")
    finally:
        repository.close()


def test_worker_honors_cancellation_requested_during_checkpoint(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")

    class CancellingHandler:
        def execute(self, job: JobRecord, checkpoint: Callable[[float | None], JobRecord]) -> None:
            repository.request_cancellation(job.id)
            checkpoint(0.25)

    try:
        queued = repository.enqueue(JobRequest(kind=JobKind.SCAN, payload={"path": "sample"}))
        worker = DurableWorker(
            repository,
            {JobKind.SCAN: CancellingHandler()},
            worker_id="worker-1",
        )

        cancelled = worker.run_once()

        assert cancelled is not None
        assert cancelled.id == queued.id
        assert cancelled.status is JobStatus.CANCELLED
    finally:
        repository.close()


def test_worker_returns_none_when_no_job_is_available(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    try:
        repository.enqueue(
            JobRequest(
                kind=JobKind.SCAN,
                payload={"path": "sample"},
                available_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        worker = DurableWorker(repository, {}, worker_id="worker-1")

        assert worker.run_once() is None
    finally:
        repository.close()
