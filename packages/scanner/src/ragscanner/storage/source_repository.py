"""SQLite persistence for non-secret source profiles and local preferences."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ragscanner.domain.helpers import is_secure_secret_reference
from ragscanner.storage.database import create_sqlite_engine
from ragscanner.storage.schema import app_settings, source_profiles

ENV_CREDENTIAL_REFERENCE_ERROR = (
    "Enter an environment-variable reference such as env:OPENWEBUI_API_KEY, not the API key "
    "itself. You can leave this field blank and connect the source later."
)


class DuplicateSourceError(ValueError):
    """The same canonical source location is already remembered."""


def normalize_env_credential_reference(value: str | None) -> str | None:
    """Normalize an optional env reference without ever accepting a raw credential value."""

    normalized = value.strip() if value else None
    if normalized and not is_env_credential_reference(normalized):
        raise ValueError(ENV_CREDENTIAL_REFERENCE_ERROR)
    return normalized


def is_env_credential_reference(value: str) -> bool:
    prefix, separator, name = value.partition(":")
    return (
        separator == ":"
        and prefix == "env"
        and bool(name)
        and (name[0].isalpha() or name[0] == "_")
        and all(
            character.isascii() and (character.isalnum() or character == "_") for character in name
        )
    )


class SourceProfile(BaseModel):
    """A remembered source location; credentials remain external references."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex, min_length=32, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(
        pattern=(
            r"^(openwebui|filesystem|qdrant|chroma|weaviate|milvus|pgvector|"
            r"elasticsearch|opensearch|pinecone|kubernetes|generic|custom)$"
        )
    )
    base_url: str | None = Field(default=None, max_length=2048)
    local_path: str | None = Field(default=None, max_length=4096)
    credential_ref: str | None = Field(default=None, max_length=500)
    discovery_origin: str = Field(default="manual", max_length=80)
    capability_status: str = Field(
        default="connection_required",
        pattern=r"^(scan_ready|metadata_only|connection_required)$",
    )
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("credential_ref")
    @classmethod
    def validate_credential_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (value.startswith("env:") and is_env_credential_reference(value)) or (
            value.startswith("file-secret:") and is_secure_secret_reference(value)
        ):
            return value
        raise ValueError(ENV_CREDENTIAL_REFERENCE_ERROR)

    @model_validator(mode="after")
    def validate_location(self) -> "SourceProfile":
        if self.kind == "filesystem" and not self.local_path:
            raise ValueError("filesystem profiles require a local path")
        if self.kind != "filesystem" and not self.base_url:
            raise ValueError("service profiles require a base URL")
        return self


class DashboardSettings(BaseModel):
    """Non-secret machine preferences used by the local dashboard."""

    model_config = ConfigDict(extra="forbid")

    locale: str = Field(default="en", pattern=r"^(en|tr|de|fr|zh-CN|it)$")
    timezone: str = Field(default="local", pattern=r"^(local|UTC)$")
    report_detail: str = Field(default="detailed", pattern=r"^(standard|detailed)$")
    rows_per_page: int = Field(default=25, ge=10, le=100)
    reduced_motion: bool = False
    show_absolute_paths: bool = False
    ai_provider: str = Field(default="ollama", max_length=80)
    ai_model: str = Field(default="llama3.1:8b", max_length=240)
    ai_base_url: str = Field(default="http://127.0.0.1:11434", max_length=2048)
    ai_credential_ref: str | None = Field(default=None, max_length=500)
    ai_remote_consent: bool = False

    @field_validator("ai_credential_ref")
    @classmethod
    def validate_ai_credential_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (value.startswith("env:") and is_env_credential_reference(value)) or (
            value.startswith("file-secret:") and is_secure_secret_reference(value)
        ):
            return value
        raise ValueError(ENV_CREDENTIAL_REFERENCE_ERROR)


class SQLiteSourceProfileRepository:
    """Persist source profiles without secret values."""

    def __init__(self, database_path: Path) -> None:
        self.engine = create_sqlite_engine(database_path.expanduser().resolve())

    def close(self) -> None:
        self.engine.dispose()

    def list(self) -> list[SourceProfile]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(source_profiles).order_by(
                    source_profiles.c.updated_at.desc(), source_profiles.c.name
                )
            ).mappings()
            return [SourceProfile.model_validate(dict(row)) for row in rows]

    def get(self, profile_id: str) -> SourceProfile | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(source_profiles).where(source_profiles.c.id == profile_id)
                )
                .mappings()
                .one_or_none()
            )
        return SourceProfile.model_validate(dict(row)) if row is not None else None

    def save(self, profile: SourceProfile) -> SourceProfile:
        now = datetime.now(UTC)
        record = profile.model_copy(update={"updated_at": now})
        values = record.model_dump(mode="json")
        with self.engine.begin() as connection:
            candidates = connection.execute(
                select(
                    source_profiles.c.id,
                    source_profiles.c.kind,
                    source_profiles.c.base_url,
                    source_profiles.c.local_path,
                ).where(source_profiles.c.id != record.id)
            ).mappings()
            identity = _source_identity(record.kind, record.local_path, record.base_url)
            if any(
                _source_identity(row["kind"], row["local_path"], row["base_url"]) == identity
                for row in candidates
            ):
                raise DuplicateSourceError("This source is already connected.")
            existing = connection.execute(
                select(source_profiles.c.id).where(source_profiles.c.id == record.id)
            ).scalar_one_or_none()
            if existing is None:
                connection.execute(insert(source_profiles).values(**values))
            else:
                connection.execute(
                    update(source_profiles)
                    .where(source_profiles.c.id == record.id)
                    .values(**values)
                )
        return record

    def delete(self, profile_id: str) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(
                delete(source_profiles).where(source_profiles.c.id == profile_id)
            )
        return bool(result.rowcount)

    def setting(self, key: str) -> str | None:
        with self.engine.connect() as connection:
            value = connection.execute(
                select(app_settings.c.value).where(app_settings.c.key == key)
            ).scalar_one_or_none()
        return str(value) if value is not None else None

    def set_setting(self, key: str, value: str) -> None:
        if not key or len(key) > 120 or len(value) > 2048:
            raise ValueError("setting is outside the supported size limit")
        with self.engine.begin() as connection:
            connection.execute(
                sqlite_insert(app_settings)
                .values(key=key, value=value, updated_at=datetime.now(UTC).isoformat())
                .on_conflict_do_update(
                    index_elements=[app_settings.c.key],
                    set_={"value": value, "updated_at": datetime.now(UTC).isoformat()},
                )
            )

    def dashboard_settings(self) -> DashboardSettings:
        value = self.setting("dashboard_settings")
        if value is None:
            return DashboardSettings()
        try:
            return DashboardSettings.model_validate_json(value)
        except ValueError:
            return DashboardSettings()

    def save_dashboard_settings(self, settings: DashboardSettings) -> None:
        self.set_setting("dashboard_settings", json.dumps(settings.model_dump(mode="json")))


def _source_identity(kind: str, local_path: str | None, base_url: str | None) -> str:
    if kind == "filesystem" and local_path:
        return f"filesystem:{os.path.normcase(str(Path(local_path).expanduser().resolve()))}"
    if base_url:
        parts = urlsplit(base_url.strip())
        host = (parts.hostname or "").casefold()
        port = parts.port
        is_default_port = (parts.scheme.casefold(), port) in {("http", 80), ("https", 443)}
        if port and not is_default_port:
            host = f"{host}:{port}"
        path = parts.path.rstrip("/")
        return f"{kind}:{urlunsplit((parts.scheme.casefold(), host, path, parts.query, ''))}"
    return f"{kind}:"
