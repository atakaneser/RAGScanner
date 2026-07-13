"""Persistence and execution ports for durable jobs."""

from datetime import datetime, timedelta
from typing import Protocol

from ragscanner.jobs.models import JobPage, JobRecord, JobRequest


class JobNotFoundError(LookupError):
    """A requested job does not exist."""


class JobLeaseLostError(RuntimeError):
    """The caller no longer owns a valid lease for the job."""


class JobStateError(RuntimeError):
    """The requested lifecycle transition is not valid."""


class JobRepository(Protocol):
    def enqueue(self, request: JobRequest, *, now: datetime | None = None) -> JobRecord: ...

    def get(self, job_id: str) -> JobRecord | None: ...

    def list(self, *, limit: int = 50, offset: int = 0) -> JobPage: ...

    def claim(
        self,
        worker_id: str,
        *,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobRecord | None: ...

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_duration: timedelta,
        progress: float | None = None,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def request_cancellation(self, job_id: str, *, now: datetime | None = None) -> JobRecord: ...

    def succeed(
        self,
        job_id: str,
        worker_id: str,
        *,
        result_ref: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def cancel(
        self,
        job_id: str,
        worker_id: str,
        *,
        result_ref: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def retry(self, job_id: str, *, now: datetime | None = None) -> JobRecord: ...
