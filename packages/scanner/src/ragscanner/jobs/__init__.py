"""Framework-independent durable job contracts."""

from ragscanner.jobs.models import JobKind, JobPage, JobRecord, JobRequest, JobStatus
from ragscanner.jobs.ports import (
    JobLeaseLostError,
    JobNotFoundError,
    JobRepository,
    JobStateError,
)

__all__ = [
    "JobKind",
    "JobLeaseLostError",
    "JobNotFoundError",
    "JobPage",
    "JobRecord",
    "JobRepository",
    "JobRequest",
    "JobStateError",
    "JobStatus",
]
