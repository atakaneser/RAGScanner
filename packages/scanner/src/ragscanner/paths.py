"""Stable per-user storage locations for RAGScanner-owned data."""

from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_data_path

APP_NAME = "RAGScanner"


def default_data_dir() -> Path:
    """Return the platform-native per-user data directory without creating it."""
    return user_data_path(APP_NAME, appauthor=False)


def reports_directory(data_dir: Path) -> Path:
    """Return the single application-owned report directory."""
    return data_dir.expanduser().resolve() / "reports"


def new_report_path(data_dir: Path, *, now: datetime | None = None) -> Path:
    """Return a collision-resistant default HTML report path."""
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S-%f")
    return reports_directory(data_dir) / f"ragscanner-report-{timestamp}.html"
