from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from ragscanner.jobs import JobKind, JobRequest
from ragscanner.jobs.models import utc_iso


def test_job_request_accepts_secret_references_and_multilingual_paths() -> None:
    request = JobRequest(
        kind=JobKind.SCAN,
        payload={
            "source_path": "知识库/Überblick.md",
            "credential_ref": "env:RAGSCANNER_SOURCE_TOKEN",
        },
        idempotency_key="scheduled:source:2026-07-14T12:00Z",
        available_at=datetime(2026, 7, 14, tzinfo=UTC),
    )

    assert request.payload["source_path"].endswith("Überblick.md")


def test_job_request_rejects_embedded_secrets_and_oversized_payloads() -> None:
    with pytest.raises(ValidationError, match="secret references"):
        JobRequest(kind=JobKind.SCAN, payload={"api_key": "sk-synthetic-secret-value"})

    with pytest.raises(ValidationError, match="exceeds"):
        JobRequest(kind=JobKind.SCAN, payload={"value": "x" * (64 * 1024)})

    with pytest.raises(ValidationError, match="JSON-compatible"):
        JobRequest(kind=JobKind.SCAN, payload={"path": Path("knowledge")})


def test_job_timestamps_are_canonicalized_to_utc_for_sqlite_ordering() -> None:
    local_time = datetime(2026, 7, 14, 15, tzinfo=timezone(timedelta(hours=3)))

    assert utc_iso(local_time) == "2026-07-14T12:00:00+00:00"
