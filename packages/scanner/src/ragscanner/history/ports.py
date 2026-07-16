"""Persistence ports kept independent from SQLite and SQLAlchemy."""

from datetime import datetime
from typing import Protocol

from ragscanner.history.models import ScanHistoryPage
from ragscanner.reporting.models import ReportDocument


class ScanHistoryRepository(Protocol):
    def save(self, report: ReportDocument) -> str: ...

    def get(self, history_id: str) -> ReportDocument | None: ...

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        source: str | None = None,
    ) -> ScanHistoryPage: ...

    def delete(self, history_id: str) -> bool: ...
