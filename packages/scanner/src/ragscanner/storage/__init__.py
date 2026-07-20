"""SQLite storage adapters for local history and durable jobs."""

from ragscanner.storage.job_repository import SQLiteJobRepository
from ragscanner.storage.machine_secrets import MachineSecretStore
from ragscanner.storage.repository import SQLiteScanHistoryRepository
from ragscanner.storage.schedule_repository import (
    ScanSchedule,
    ScanScheduleRequest,
    SQLiteScheduleRepository,
)
from ragscanner.storage.source_repository import (
    ENV_CREDENTIAL_REFERENCE_ERROR,
    DashboardSettings,
    DuplicateSourceError,
    SourceProfile,
    SQLiteSourceProfileRepository,
    normalize_env_credential_reference,
)

__all__ = [
    "ENV_CREDENTIAL_REFERENCE_ERROR",
    "DashboardSettings",
    "DuplicateSourceError",
    "MachineSecretStore",
    "SQLiteJobRepository",
    "SQLiteScanHistoryRepository",
    "SQLiteScheduleRepository",
    "SQLiteSourceProfileRepository",
    "ScanSchedule",
    "ScanScheduleRequest",
    "SourceProfile",
    "normalize_env_credential_reference",
]
