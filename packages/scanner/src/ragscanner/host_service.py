"""Machine-wide local Host Service registration.

This is intentionally separate from the desktop Agent. It is for an always-on
RAG host such as Docker-backed OpenWebUI, and is installed only by an elevated
administrator command.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE_NAME = "ragscanner-host"
WINDOWS_SERVICE_NAME = "RAGScannerHost"


def _program(name: str) -> str:
    return shutil.which(name) or name


def system_data_dir(*, platform: str | None = None) -> Path:
    selected = platform or sys.platform
    if selected == "win32":
        return Path(os.environ.get("ProgramData", r"C:\\ProgramData")) / "RAGScanner"
    if selected == "darwin":
        return Path("/Library/Application Support/RAGScanner")
    return Path("/var/lib/ragscanner")


def service_definition_path(*, platform: str | None = None) -> Path:
    selected = platform or sys.platform
    if selected == "win32":
        return system_data_dir(platform=selected) / "service-command.txt"
    if selected == "darwin":
        return Path("/Library/LaunchDaemons/com.ragscanner.host.plist")
    return Path("/etc/systemd/system/ragscanner-host.service")


def is_elevated(*, platform: str | None = None) -> bool:
    selected = platform or sys.platform
    if selected == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return False
    return os.geteuid() == 0


def install_host_service(*, platform: str | None = None) -> Path:
    """Register and start the elevated, machine-wide Host Service."""
    selected = platform or sys.platform
    if not is_elevated(platform=selected):
        raise PermissionError("machine-wide service installation requires administrator permission")
    data_dir = system_data_dir(platform=selected)
    data_dir.mkdir(parents=True, exist_ok=True)
    definition = service_definition_path(platform=selected)
    command = f'"{sys.executable}" -m ragscanner host run --data-dir "{data_dir}"'
    if selected == "win32":
        definition.write_text(command + "\n", encoding="utf-8")
        subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned command
            [
                _program("sc.exe"),
                "create",
                WINDOWS_SERVICE_NAME,
                f"binPath= {command}",
                "start= auto",
            ],
            check=False,
        )
        subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned service
            [_program("sc.exe"), "start", WINDOWS_SERVICE_NAME], check=False
        )
        return definition
    if selected == "darwin":
        definition.parent.mkdir(parents=True, exist_ok=True)
        definition.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict><key>Label</key><string>com.ragscanner.host</string>'
            f"<key>ProgramArguments</key><array><string>{sys.executable}</string><string>-m</string>"
            "<string>ragscanner</string><string>host</string><string>run</string><string>--data-dir</string>"
            f"<string>{data_dir}</string></array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
            "</dict></plist>\n",
            encoding="utf-8",
        )
        subprocess.run(  # noqa: S603 - fixed platform utility and product-owned plist
            [_program("launchctl"), "bootstrap", "system", str(definition)], check=False
        )
        return definition
    definition.parent.mkdir(parents=True, exist_ok=True)
    definition.write_text(
        "[Unit]\nDescription=RAGScanner machine-local Host Service\nAfter=network-online.target\n\n"
        "[Service]\nType=simple\nDynamicUser=yes\nStateDirectory=ragscanner\n"
        "NoNewPrivileges=yes\nPrivateTmp=yes\nProtectSystem=strict\n"
        f"ExecStart={command}\nRestart=on-failure\nRestartSec=3\n\n"
        "[Install]\nWantedBy=multi-user.target\n",
        encoding="utf-8",
    )
    subprocess.run(  # noqa: S603 - fixed platform utility
        [_program("systemctl"), "daemon-reload"], check=False
    )
    subprocess.run(  # noqa: S603 - fixed service name
        [_program("systemctl"), "enable", "--now", SERVICE_NAME], check=False
    )
    return definition


def remove_host_service(*, platform: str | None = None) -> None:
    """Stop and remove RAGScanner's machine-wide service definition only."""
    selected = platform or sys.platform
    if not is_elevated(platform=selected):
        raise PermissionError("machine-wide service removal requires administrator permission")
    definition = service_definition_path(platform=selected)
    if selected == "win32":
        subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned service
            [_program("sc.exe"), "stop", WINDOWS_SERVICE_NAME], check=False
        )
        subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned service
            [_program("sc.exe"), "delete", WINDOWS_SERVICE_NAME], check=False
        )
    elif selected == "darwin":
        subprocess.run(  # noqa: S603 - fixed platform utility and product-owned plist
            [_program("launchctl"), "bootout", "system", str(definition)], check=False
        )
    else:
        subprocess.run(  # noqa: S603 - fixed service name
            [_program("systemctl"), "disable", "--now", SERVICE_NAME], check=False
        )
        subprocess.run(  # noqa: S603 - fixed platform utility
            [_program("systemctl"), "daemon-reload"], check=False
        )
    definition.unlink(missing_ok=True)
