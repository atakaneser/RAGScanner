"""SQLite persistence for non-secret source profiles and local preferences."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ragscanner.storage.database import create_sqlite_engine
from ragscanner.storage.schema import app_settings, source_profiles

ENV_CREDENTIAL_REFERENCE_ERROR = (
    "Enter an environment-variable reference such as env:OPENWEBUI_API_KEY, not the API key "
    "itself. You can leave this field blank and connect the source later."
)


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
        pattern=r"^(openwebui|filesystem|qdrant|chroma|weaviate|milvus|pgvector|generic)$"
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
        return normalize_env_credential_reference(value)

    @model_validator(mode="after")
    def validate_location(self) -> "SourceProfile":
        if self.kind == "filesystem" and not self.local_path:
            raise ValueError("filesystem profiles require a local path")
        if self.kind != "filesystem" and not self.base_url:
            raise ValueError("service profiles require a base URL")
        return self


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
