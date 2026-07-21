"""Canonical loopback-only dashboard address and legacy hostname cleanup."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DASHBOARD_BIND_HOST = "127.0.0.1"
DASHBOARD_PORT = 8765
_LEGACY_DASHBOARD_HOST = "local.ragscanner.com"
_LEGACY_HOSTS_MARKER = "# RAGScanner local dashboard"
_LEGACY_HOSTS_LINE = f"127.0.0.1 {_LEGACY_DASHBOARD_HOST} {_LEGACY_HOSTS_MARKER}"


def dashboard_url() -> str:
    """Return the one supported dashboard URL."""
    return f"http://localhost:{DASHBOARD_PORT}"


def hosts_file_path(*, platform: str | None = None) -> Path:
    """Return the platform hosts file path for legacy-entry cleanup only."""
    selected = platform or sys.platform
    if selected == "win32":
        root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        return root / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def remove_legacy_hostname(path: Path) -> bool:
    """Remove only the obsolete RAGScanner-owned hosts-file line."""
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    retained = [line for line in content.splitlines() if line.strip() != _LEGACY_HOSTS_LINE]
    if len(retained) == len(content.splitlines()):
        return False
    path.write_text("\n".join(retained) + ("\n" if retained else ""), encoding="utf-8")
    return True
