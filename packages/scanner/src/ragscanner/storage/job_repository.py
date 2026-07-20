"""SQLite implementation of the durable job repository port."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import Integer, and_, case, cast, func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ragscanner.jobs import (
    JobLeaseLostError,
    JobNotFoundError,
    JobPage,
    JobRecord,
    JobRequest,
    JobStateError,
    JobStatus,
)
from ragscanner.jobs.models import utc_iso
from ragscanner.storage.database import create_sqlite_engine
from ragscanner.storage.schema import jobs


class SQLiteJobRepository:
    """Persist jobs and enforce atomic lease-based lifecycle transitions."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.expanduser().resolve()
        self.engine = create_sqlite_engine(self.database_path)

    def close(self) -> None:
        self.engine.dispose()

    def enqueue(self, request: JobRequest, *, now: datetime | None = None) -> JobRecord:
        current = _now(now)
        available = request.available_at or current
        payload = json.dumps(
            request.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.engine.begin() as connection:
            job_id = uuid4().hex
            sequence = connection.execute(
                select(func.max(cast(func.substr(jobs.c.display_id, 9), Integer)))
            ).scalar_one_or_none()
            display_id = f"RAGSCN-{(sequence or 0) + 1:04d}"
            statement = sqlite_insert(jobs).values(
                id=job_id,
                display_id=display_id,
                kind=request.kind.value,
                status=JobStatus.QUEUED.value,
                payload_json=payload,
                idempotency_key=request.idempotency_key,
                attempt_count=0,
                max_attempts=request.max_attempts,
                created_at=utc_iso(current),
                updated_at=utc_iso(current),
                available_at=utc_iso(available),
                progress=0,
            )
            if request.idempotency_key is not None:
                statement = statement.on_conflict_do_nothing(
                    index_elements=[jobs.c.kind, jobs.c.idempotency_key]
                )
            connection.execute(statement)
            if request.idempotency_key is None:
                row = connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one()
            else:
                row = (
                    connection.execute(
                        select(jobs).where(
                            jobs.c.kind == request.kind.value,
                            jobs.c.idempotency_key == request.idempotency_key,
                        )
                    )
                    .mappings()
                    .one()
                )
                if row["payload_json"] != payload or row["max_attempts"] != request.max_attempts:
                    raise JobStateError(
                        "The idempotency key is already associated with different job parameters."
                    )
        return _record(row)

    def get(self, job_id: str) -> JobRecord | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one_or_none()
            )
        return _record(row) if row is not None else None

    def list(self, *, limit: int = 50, offset: int = 0) -> JobPage:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        with self.engine.connect() as connection:
            total = connection.execute(select(func.count()).select_from(jobs)).scalar_one()
            rows = connection.execute(
                select(jobs)
                .order_by(jobs.c.created_at.desc(), jobs.c.id.desc())
                .limit(limit)
                .offset(offset)
            ).mappings()
            items = [_record(row) for row in rows]
        return JobPage(items=items, total=total, limit=limit, offset=offset)

    def claim(
        self,
        worker_id: str,
        *,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobRecord | None:
        _validate_worker(worker_id)
        _validate_lease(lease_duration)
        current = _now(now)
        current_iso = utc_iso(current)
        expiry_iso = utc_iso(current + lease_duration)
        active = (JobStatus.RUNNING.value, JobStatus.CANCEL_REQUESTED.value)
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.status == JobStatus.CANCEL_REQUESTED.value,
                    jobs.c.lease_expires_at <= current_iso,
                )
                .values(
                    status=JobStatus.CANCELLED.value,
                    completed_at=current_iso,
                    updated_at=current_iso,
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                )
            )
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.status == JobStatus.RUNNING.value,
                    jobs.c.lease_expires_at <= current_iso,
                    jobs.c.attempt_count >= jobs.c.max_attempts,
                )
                .values(
                    status=JobStatus.FAILED.value,
                    completed_at=current_iso,
                    updated_at=current_iso,
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                    error_code="lease_expired",
                    error_message="The job exhausted its attempts after a worker lease expired.",
                )
            )
            candidate = (
                select(jobs.c.id)
                .where(
                    jobs.c.attempt_count < jobs.c.max_attempts,
                    or_(
                        and_(
                            jobs.c.status == JobStatus.QUEUED.value,
                            jobs.c.available_at <= current_iso,
                        ),
                        and_(jobs.c.status.in_(active), jobs.c.lease_expires_at <= current_iso),
                    ),
                )
                .order_by(jobs.c.available_at, jobs.c.created_at, jobs.c.id)
                .limit(1)
                .scalar_subquery()
            )
            row = (
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == candidate)
                    .values(
                        status=case(
                            (
                                jobs.c.status == JobStatus.CANCEL_REQUESTED.value,
                                JobStatus.CANCEL_REQUESTED.value,
                            ),
                            else_=JobStatus.RUNNING.value,
                        ),
                        attempt_count=jobs.c.attempt_count + 1,
                        started_at=func.coalesce(jobs.c.started_at, current_iso),
                        updated_at=current_iso,
                        lease_owner=worker_id,
                        lease_expires_at=expiry_iso,
                        heartbeat_at=current_iso,
                        error_code=None,
                        error_message=None,
                    )
                    .returning(*jobs.c)
                )
                .mappings()
                .one_or_none()
            )
        return _record(row) if row is not None else None

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_duration: timedelta,
        progress: float | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        _validate_worker(worker_id)
        _validate_lease(lease_duration)
        if progress is not None and not 0 <= progress <= 1:
            raise ValueError("progress must be between 0 and 1")
        current = _now(now)
        current_iso = utc_iso(current)
        values: dict[str, Any] = {
            "heartbeat_at": current_iso,
            "lease_expires_at": utc_iso(current + lease_duration),
            "updated_at": current_iso,
        }
        if progress is not None:
            values["progress"] = progress
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    update(jobs)
                    .where(
                        jobs.c.id == job_id,
                        jobs.c.lease_owner == worker_id,
                        jobs.c.status.in_(
                            (JobStatus.RUNNING.value, JobStatus.CANCEL_REQUESTED.value)
                        ),
                        jobs.c.lease_expires_at > current_iso,
                    )
                    .values(**values)
                    .returning(*jobs.c)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise JobLeaseLostError("The worker no longer owns a valid job lease.")
        return _record(row)

    def request_cancellation(self, job_id: str, *, now: datetime | None = None) -> JobRecord:
        current_iso = utc_iso(_now(now))
        with self.engine.begin() as connection:
            existing = (
                connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one_or_none()
            )
            if existing is None:
                raise JobNotFoundError("The requested job does not exist.")
            status = JobStatus(existing["status"])
            if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
                return _record(existing)
            if status is JobStatus.QUEUED:
                values = {
                    "status": JobStatus.CANCELLED.value,
                    "completed_at": current_iso,
                    "updated_at": current_iso,
                }
            else:
                values = {
                    "status": JobStatus.CANCEL_REQUESTED.value,
                    "updated_at": current_iso,
                }
            row = (
                connection.execute(
                    update(jobs).where(jobs.c.id == job_id).values(**values).returning(*jobs.c)
                )
                .mappings()
                .one()
            )
        return _record(row)

    def succeed(
        self,
        job_id: str,
        worker_id: str,
        *,
        result_ref: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        return self._finish(
            job_id,
            worker_id,
            expected=JobStatus.RUNNING,
            target=JobStatus.SUCCEEDED,
            now=now,
            result_ref=result_ref,
            progress=1,
        )

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
        now: datetime | None = None,
    ) -> JobRecord:
        if not error_code or len(error_code) > 80:
            raise ValueError("error_code must contain at most 80 characters")
        if not error_message or len(error_message) > 500:
            raise ValueError("error_message must contain at most 500 characters")
        current = _now(now)
        current_iso = utc_iso(current)
        with self.engine.begin() as connection:
            existing = self._leased_row(connection, job_id, worker_id, current_iso)
            if JobStatus(existing["status"]) is not JobStatus.RUNNING:
                raise JobStateError(
                    "A cancellation-requested job cannot be failed as ordinary work."
                )
            exhausted = int(existing["attempt_count"]) >= int(existing["max_attempts"])
            row = (
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == job_id, jobs.c.lease_owner == worker_id)
                    .values(
                        status=(JobStatus.FAILED.value if exhausted else JobStatus.QUEUED.value),
                        available_at=utc_iso(
                            current
                            + timedelta(seconds=min(2 ** int(existing["attempt_count"]), 60))
                        ),
                        completed_at=current_iso if exhausted else None,
                        updated_at=current_iso,
                        lease_owner=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                        error_code=error_code,
                        error_message=error_message,
                    )
                    .returning(*jobs.c)
                )
                .mappings()
                .one()
            )
        return _record(row)

    def cancel(
        self,
        job_id: str,
        worker_id: str,
        *,
        result_ref: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        return self._finish(
            job_id,
            worker_id,
            expected=JobStatus.CANCEL_REQUESTED,
            target=JobStatus.CANCELLED,
            now=now,
            result_ref=result_ref,
        )

    def retry(self, job_id: str, *, now: datetime | None = None) -> JobRecord:
        current_iso = utc_iso(_now(now))
        with self.engine.begin() as connection:
            existing = (
                connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one_or_none()
            )
            if existing is None:
                raise JobNotFoundError("The requested job does not exist.")
            if JobStatus(existing["status"]) not in {JobStatus.FAILED, JobStatus.CANCELLED}:
                raise JobStateError("Only failed or cancelled jobs can be retried.")
            row = (
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == job_id)
                    .values(
                        status=JobStatus.QUEUED.value,
                        attempt_count=0,
                        available_at=current_iso,
                        updated_at=current_iso,
                        started_at=None,
                        completed_at=None,
                        progress=0,
                        result_ref=None,
                        error_code=None,
                        error_message=None,
                        lease_owner=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                    )
                    .returning(*jobs.c)
                )
                .mappings()
                .one()
            )
        return _record(row)

    def _finish(
        self,
        job_id: str,
        worker_id: str,
        *,
        expected: JobStatus,
        target: JobStatus,
        now: datetime | None,
        result_ref: str | None = None,
        progress: float | None = None,
    ) -> JobRecord:
        current_iso = utc_iso(_now(now))
        with self.engine.begin() as connection:
            existing = self._leased_row(connection, job_id, worker_id, current_iso)
            if JobStatus(existing["status"]) is not expected:
                raise JobStateError(
                    f"The job cannot transition from {existing['status']} to {target.value}."
                )
            values: dict[str, Any] = {
                "status": target.value,
                "completed_at": current_iso,
                "updated_at": current_iso,
                "lease_owner": None,
                "lease_expires_at": None,
                "heartbeat_at": None,
                "result_ref": result_ref,
            }
            if progress is not None:
                values["progress"] = progress
            row = (
                connection.execute(
                    update(jobs).where(jobs.c.id == job_id).values(**values).returning(*jobs.c)
                )
                .mappings()
                .one()
            )
        return _record(row)

    @staticmethod
    def _leased_row(connection: Any, job_id: str, worker_id: str, current_iso: str) -> Any:
        row = connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one_or_none()
        if row is None:
            raise JobNotFoundError("The requested job does not exist.")
        if (
            row["lease_owner"] != worker_id
            or not row["lease_expires_at"]
            or row["lease_expires_at"] <= current_iso
        ):
            raise JobLeaseLostError("The worker no longer owns a valid job lease.")
        return row


def _record(row: Any) -> JobRecord:
    return JobRecord(
        id=row["id"],
        display_id=row["display_id"],
        kind=row["kind"],
        status=row["status"],
        payload=json.loads(row["payload_json"]),
        idempotency_key=row["idempotency_key"],
        attempt_count=row["attempt_count"],
        max_attempts=row["max_attempts"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        available_at=row["available_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        lease_owner=row["lease_owner"],
        lease_expires_at=row["lease_expires_at"],
        heartbeat_at=row["heartbeat_at"],
        progress=row["progress"],
        result_ref=row["result_ref"],
        error_code=row["error_code"],
        error_message=row["error_message"],
    )


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("job timestamps must be timezone-aware")
    return current.astimezone(UTC)


def _validate_worker(worker_id: str) -> None:
    if not 1 <= len(worker_id) <= 160:
        raise ValueError("worker_id must contain between 1 and 160 characters")


def _validate_lease(duration: timedelta) -> None:
    if not timedelta(seconds=5) <= duration <= timedelta(hours=1):
        raise ValueError("lease_duration must be between 5 seconds and 1 hour")
