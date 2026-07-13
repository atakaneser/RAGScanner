"""Framework-independent durable job models and lifecycle rules."""

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from ragscanner.domain.helpers import contains_unreferenced_secret

MAX_JOB_PAYLOAD_BYTES = 64 * 1024


class JobKind(StrEnum):
    SCAN = "scan"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_JOB_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED})


class JobRequest(BaseModel):
    """Validated non-secret work description accepted by the durable queue."""

    model_config = ConfigDict(extra="forbid")

    kind: JobKind
    payload: dict[str, Any]
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)
    max_attempts: int = Field(default=3, ge=1, le=10)
    available_at: AwareDatetime | None = None

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if contains_unreferenced_secret(payload):
            raise ValueError("job payloads may contain secret references but not secret values")
        try:
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        except TypeError as error:
            raise ValueError("job payloads must contain only JSON-compatible values") from error
        if len(encoded) > MAX_JOB_PAYLOAD_BYTES:
            raise ValueError(f"job payload exceeds {MAX_JOB_PAYLOAD_BYTES} bytes")
        return payload


class JobRecord(BaseModel):
    """Stable application view of a persisted job execution."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: JobKind
    status: JobStatus
    payload: dict[str, Any]
    idempotency_key: str | None = None
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    created_at: AwareDatetime
    updated_at: AwareDatetime
    available_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    lease_owner: str | None = None
    lease_expires_at: AwareDatetime | None = None
    heartbeat_at: AwareDatetime | None = None
    progress: float = Field(default=0, ge=0, le=1)
    result_ref: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "JobRecord":
        leased = self.status in {JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED}
        if leased and (self.lease_owner is None or self.lease_expires_at is None):
            raise ValueError("active jobs require a lease owner and expiration")
        if self.status in TERMINAL_JOB_STATUSES and self.completed_at is None:
            raise ValueError("terminal jobs require a completion time")
        return self


class JobPage(BaseModel):
    items: list[JobRecord]
    total: int = Field(ge=0)
    limit: int = Field(gt=0, le=200)
    offset: int = Field(ge=0)


def utc_iso(value: datetime) -> str:
    """Serialize aware UTC timestamps consistently for SQLite ordering."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("job timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()
