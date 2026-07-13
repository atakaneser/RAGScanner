"""Persistence ports kept independent from SQLite and SQLAlchemy."""

from typing import Protocol

from ragscanner.history.models import ScanHistoryPage
from ragscanner.reporting.models import ReportDocument


class ScanHistoryRepository(Protocol):
    def save(self, report: ReportDocument) -> str: ...

    def get(self, history_id: str) -> ReportDocument | None: ...

    def list(self, *, limit: int = 50, offset: int = 0) -> ScanHistoryPage: ...

    def delete(self, history_id: str) -> bool: ...
