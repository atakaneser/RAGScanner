"""Stable machine data and per-user cache locations for RAGScanner-owned data."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_cache_path

APP_NAME = "RAGScanner"


def system_data_dir(*, platform: str | None = None) -> Path:
    """Return the machine-owned persistent data root without creating it."""

    selected = platform or sys.platform
    if selected == "win32":
        return Path(os.environ.get("ProgramData", r"C:\\ProgramData")) / APP_NAME
    if selected == "darwin":
        return Path("/Library/Application Support/RAGScanner")
    return Path("/var/lib/ragscanner")


def default_data_dir() -> Path:
    """Return the machine-owned persistent data directory."""

    return system_data_dir()


def user_cache_dir() -> Path:
    """Return the signed-in user's disposable UI/CLI cache directory."""

    return user_cache_path(APP_NAME, appauthor=False)


def service_temp_dir(data_dir: Path) -> Path:
    """Return a service-owned temporary directory independent of desktop logon."""

    return data_dir.expanduser().resolve() / "temp"


def reports_directory(data_dir: Path) -> Path:
    """Return the single application-owned report directory."""
    return data_dir.expanduser().resolve() / "reports"


def new_report_path(data_dir: Path, *, now: datetime | None = None) -> Path:
    """Return a collision-resistant default HTML report path."""
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S-%f")
    return reports_directory(data_dir) / f"ragscanner-report-{timestamp}.html"
