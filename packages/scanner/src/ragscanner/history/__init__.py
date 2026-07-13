"""Database-independent scan history and comparison contracts."""

from ragscanner.history.models import (
    FindingChange,
    ScanComparison,
    ScanHistoryPage,
    ScanHistorySummary,
    ScoreChange,
)
from ragscanner.history.ports import ScanHistoryRepository
from ragscanner.history.service import compare_scans

__all__ = [
    "FindingChange",
    "ScanComparison",
    "ScanHistoryPage",
    "ScanHistoryRepository",
    "ScanHistorySummary",
    "ScoreChange",
    "compare_scans",
]
