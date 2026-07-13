"""Stable API-only envelopes that do not leak framework or database errors."""

from pydantic import BaseModel, ConfigDict, Field

from ragscanner.jobs import JobRecord


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiError(BaseModel):
    error: ApiErrorDetail


class ApiHealth(BaseModel):
    status: str = "ok"
    api_version: str
    access_mode: str = "localhost_read_only"


class LocalScanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)
    config_path: str | None = Field(default=None, min_length=1, max_length=4096)
    max_attempts: int = Field(default=3, ge=1, le=10)


class OpenWebUIScanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(min_length=1, max_length=2048)
    knowledge_id: str = Field(min_length=1, max_length=240)
    credential_ref: str = Field(min_length=1, max_length=500)
    content_consent: bool
    max_attempts: int = Field(default=3, ge=1, le=10)


class JobAccepted(BaseModel):
    job: JobRecord
