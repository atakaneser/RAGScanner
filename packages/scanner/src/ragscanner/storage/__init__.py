"""SQLite storage adapters for local history and durable jobs."""

from ragscanner.storage.job_repository import SQLiteJobRepository
from ragscanner.storage.repository import SQLiteScanHistoryRepository
from ragscanner.storage.source_repository import (
    ENV_CREDENTIAL_REFERENCE_ERROR,
    SourceProfile,
    SQLiteSourceProfileRepository,
    normalize_env_credential_reference,
)

__all__ = [
    "ENV_CREDENTIAL_REFERENCE_ERROR",
    "SQLiteJobRepository",
    "SQLiteScanHistoryRepository",
    "SQLiteSourceProfileRepository",
    "SourceProfile",
    "normalize_env_credential_reference",
]
