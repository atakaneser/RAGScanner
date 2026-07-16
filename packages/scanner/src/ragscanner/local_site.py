"""Machine-local dashboard hostname registration.

This module never changes DNS or contacts the network. A host installation may
opt in to a marked loopback entry in the operating system hosts file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

LOCAL_DASHBOARD_HOST = "local.ragscanner.com"
_HOSTS_MARKER = "# RAGScanner local dashboard"
_HOSTS_LINE = f"127.0.0.1 {LOCAL_DASHBOARD_HOST} {_HOSTS_MARKER}"


def dashboard_url(*, port: int = 8000) -> str:
    """Return the local-only dashboard URL without making a network request."""
    suffix = "" if port == 80 else f":{port}"
    return f"http://{LOCAL_DASHBOARD_HOST}{suffix}"


def hosts_file_path(*, platform: str | None = None) -> Path:
    """Return the platform hosts file path."""
    selected = platform or sys.platform
    if selected == "win32":
        root = Path(os.environ.get("SystemRoot", r"C:\\Windows"))
        return root / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def local_hostname_is_registered(path: Path) -> bool:
    """Check only RAGScanner's explicit hosts entry."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    return any(line.strip() == _HOSTS_LINE for line in lines)


def register_local_hostname(path: Path) -> None:
    """Add RAGScanner's idempotent loopback mapping to an approved hosts file."""
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip() == _HOSTS_LINE for line in content.splitlines()):
        return
    suffix = "" if not content or content.endswith("\n") else "\n"
    path.write_text(f"{content}{suffix}{_HOSTS_LINE}\n", encoding="utf-8")


def unregister_local_hostname(path: Path) -> None:
    """Remove only the exact marker line owned by RAGScanner."""
    content = path.read_text(encoding="utf-8")
    retained = [line for line in content.splitlines() if line.strip() != _HOSTS_LINE]
    path.write_text("\n".join(retained) + ("\n" if retained else ""), encoding="utf-8")
