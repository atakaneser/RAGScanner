"""Application services for durable background job execution."""

from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Protocol

from ragscanner.jobs import JobKind, JobRecord, JobRepository, JobStatus

JobCheckpoint = Callable[[float | None], JobRecord]


class JobCancellationRequested(RuntimeError):
    """Cooperative signal raised when a handler reaches a cancelled checkpoint."""

    def __init__(self, result_ref: str | None = None) -> None:
        self.result_ref = result_ref
        super().__init__("Job cancellation was requested.")


class JobHandler(Protocol):
    def execute(self, job: JobRecord, checkpoint: JobCheckpoint) -> str | None: ...


class DurableWorker:
    """Claim and execute at most one job using a renewable database lease."""

    def __init__(
        self,
        repository: JobRepository,
        handlers: Mapping[JobKind, JobHandler],
        *,
        worker_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
    ) -> None:
        self.repository = repository
        self.handlers = dict(handlers)
        self.worker_id = worker_id
        self.lease_duration = lease_duration

    def run_once(self) -> JobRecord | None:
        job = self.repository.claim(
            self.worker_id,
            lease_duration=self.lease_duration,
        )
        if job is None:
            return None
        if job.status is JobStatus.CANCEL_REQUESTED:
            return self.repository.cancel(job.id, self.worker_id)

        handler = self.handlers.get(job.kind)
        if handler is None:
            return self.repository.fail(
                job.id,
                self.worker_id,
                error_code="unsupported_job_kind",
                error_message="No worker handler is registered for this job kind.",
            )

        def checkpoint(progress: float | None = None) -> JobRecord:
            current = self.repository.heartbeat(
                job.id,
                self.worker_id,
                lease_duration=self.lease_duration,
                progress=progress,
            )
            if current.status is JobStatus.CANCEL_REQUESTED:
                raise JobCancellationRequested
            return current

        try:
            checkpoint(0)
            result_ref = handler.execute(job, checkpoint)
            checkpoint(1)
        except JobCancellationRequested as error:
            return self.repository.cancel(
                job.id,
                self.worker_id,
                result_ref=error.result_ref,
            )
        except Exception:
            return self.repository.fail(
                job.id,
                self.worker_id,
                error_code="job_execution_failed",
                error_message="The job handler failed without exposing untrusted exception details.",
            )
        return self.repository.succeed(
            job.id,
            self.worker_id,
            result_ref=result_ref,
        )
