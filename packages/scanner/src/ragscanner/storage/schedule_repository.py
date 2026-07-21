"""SQLite-backed recurring scan schedule persistence and materialization."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Integer, cast, delete, func, insert, select, update

from ragscanner.domain.helpers import contains_unreferenced_secret
from ragscanner.jobs import JobKind, JobRequest
from ragscanner.storage.database import create_sqlite_engine
from ragscanner.storage.schema import schedules


class ScanSchedule(BaseModel):
    """A persisted recurring scan definition with its next due time."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_id: str = Field(pattern=r"^RAGSCH-[0-9]{4,}$")
    name: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any]
    interval_minutes: int = Field(ge=15, le=525600)
    enabled: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime
    next_run_at: AwareDatetime
    last_run_at: AwareDatetime | None = None


class ScanScheduleRequest(BaseModel):
    """Validated input for one recurring scan."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any]
    interval_minutes: int = Field(ge=15, le=525600)

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        JobRequest(kind=JobKind.SCAN, payload=payload)
        if contains_unreferenced_secret(payload):
            raise ValueError("schedule payloads may contain references but not secret values")
        return payload


class SQLiteScheduleRepository:
    """Store schedules and atomically advance due occurrences."""

    def __init__(self, database_path: Path) -> None:
        self.engine = create_sqlite_engine(database_path.expanduser().resolve())

    def close(self) -> None:
        self.engine.dispose()

    def create(self, request: ScanScheduleRequest, *, now: datetime | None = None) -> ScanSchedule:
        current = _now(now)
        with self.engine.begin() as connection:
            sequence = connection.execute(
                select(func.max(cast(func.substr(schedules.c.display_id, 8), Integer)))
            ).scalar_one_or_none()
            schedule_id = uuid4().hex
            connection.execute(
                insert(schedules).values(
                    id=schedule_id,
                    display_id=f"RAGSCH-{(sequence or 0) + 1:04d}",
                    name=request.name,
                    payload_json=json.dumps(
                        request.payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    interval_minutes=request.interval_minutes,
                    enabled=True,
                    created_at=current.isoformat(),
                    updated_at=current.isoformat(),
                    next_run_at=(current + timedelta(minutes=request.interval_minutes)).isoformat(),
                )
            )
            row = (
                connection.execute(select(schedules).where(schedules.c.id == schedule_id))
                .mappings()
                .one()
            )
        return _schedule(row)

    def list(self, *, limit: int = 100) -> list[ScanSchedule]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(schedules)
                .order_by(schedules.c.created_at.desc(), schedules.c.id.desc())
                .limit(limit)
            ).mappings()
            return [_schedule(row) for row in rows]

    def delete(self, schedule_id: str) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(delete(schedules).where(schedules.c.id == schedule_id))
        return bool(result.rowcount)

    def set_enabled(self, schedule_id: str, enabled: bool) -> bool:
        now = datetime.now(UTC).isoformat()
        with self.engine.begin() as connection:
            result = connection.execute(
                update(schedules)
                .where(schedules.c.id == schedule_id)
                .values(
                    enabled=enabled,
                    updated_at=now,
                    next_run_at=now if enabled else schedules.c.next_run_at,
                )
            )
        return bool(result.rowcount)

    def update_schedule(
        self,
        schedule_id: str,
        *,
        name: str,
        interval_minutes: int,
        next_run_at: datetime,
    ) -> bool:
        """Update recurrence and the next explicit execution time."""

        clean_name = name.strip()
        if not clean_name or len(clean_name) > 160:
            raise ValueError("schedule name must contain 1-160 characters")
        if not 15 <= interval_minutes <= 525600:
            raise ValueError("schedule interval must be between 15 and 525600 minutes")
        next_run = _now(next_run_at)
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            result = connection.execute(
                update(schedules)
                .where(schedules.c.id == schedule_id)
                .values(
                    name=clean_name,
                    interval_minutes=interval_minutes,
                    next_run_at=next_run.isoformat(),
                    updated_at=now.isoformat(),
                )
            )
        return bool(result.rowcount)

    def materialize_due(self, job_repository: Any, *, now: datetime | None = None) -> int:
        current = _now(now)
        created = 0
        with self.engine.begin() as connection:
            rows = list(
                connection.execute(
                    select(schedules)
                    .where(
                        schedules.c.enabled.is_(True),
                        schedules.c.next_run_at <= current.isoformat(),
                    )
                    .order_by(schedules.c.next_run_at, schedules.c.id)
                ).mappings()
            )
            for row in rows:
                occurrence = str(row["next_run_at"])
                payload = json.loads(row["payload_json"])
                job_repository.enqueue(
                    JobRequest(
                        kind=JobKind.SCAN,
                        payload=payload,
                        idempotency_key=f"schedule:{row['id']}:{occurrence}",
                    ),
                    now=current,
                )
                next_run = datetime.fromisoformat(occurrence)
                interval = timedelta(minutes=int(row["interval_minutes"]))
                while next_run <= current:
                    next_run += interval
                connection.execute(
                    update(schedules)
                    .where(schedules.c.id == row["id"], schedules.c.next_run_at == occurrence)
                    .values(
                        last_run_at=current.isoformat(),
                        next_run_at=next_run.isoformat(),
                        updated_at=current.isoformat(),
                    )
                )
                created += 1
        return created


def _schedule(row: Any) -> ScanSchedule:
    return ScanSchedule(
        id=row["id"],
        display_id=row["display_id"],
        name=row["name"],
        payload=json.loads(row["payload_json"]),
        interval_minutes=row["interval_minutes"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_run_at=row["next_run_at"],
        last_run_at=row["last_run_at"],
    )


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("schedule timestamps must be timezone-aware")
    return current.astimezone(UTC)
