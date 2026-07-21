"""Per-user local Agent lifecycle and platform autostart integration.

The Agent deliberately remains a delivery concern.  It owns the localhost web
server and a single durable-job worker; scanner Core remains unaware of it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path

import uvicorn

from ragscanner.api import create_app
from ragscanner.application import DurableWorker, StaticScanApplicationService, StaticScanJobHandler
from ragscanner.jobs import JobKind
from ragscanner.local_site import DASHBOARD_BIND_HOST, DASHBOARD_PORT
from ragscanner.storage import (
    SQLiteJobRepository,
    SQLiteScanHistoryRepository,
    SQLiteScheduleRepository,
)

AGENT_LABEL = "RAGScanner Agent"
SERVICE_NAME = "ragscanner-agent"


def _program(name: str) -> str:
    """Resolve a platform utility to avoid shell execution and PATH ambiguity."""
    return shutil.which(name) or name


def platform_autostart_path(data_dir: Path, *, platform: str | None = None) -> Path:
    """Return the user-owned registration file for the current platform."""
    selected = platform or sys.platform
    if selected == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / "com.ragscanner.agent.plist"
    if selected == "win32":
        return data_dir / "agent" / "ragscanner-agent.xml"
    return Path.home() / ".config" / "systemd" / "user" / f"{SERVICE_NAME}.service"


def _command() -> str:
    # sys.executable keeps the command in the same uv-managed tool environment.
    return f'"{sys.executable}" -m ragscanner agent run'


def install_autostart(data_dir: Path, *, platform: str | None = None) -> Path:
    """Install a per-user autostart record without requiring administrator rights."""
    selected = platform or sys.platform
    path = platform_autostart_path(data_dir, platform=selected)
    path.parent.mkdir(parents=True, exist_ok=True)
    command = _command()
    if selected == "darwin":
        path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict><key>Label</key><string>com.ragscanner.agent</string>'
            f"<key>ProgramArguments</key><array><string>{sys.executable}</string><string>-m</string>"
            "<string>ragscanner</string><string>agent</string><string>run</string></array>"
            "<key>RunAtLoad</key><true/><key>KeepAlive</key><true/></dict></plist>\n",
            encoding="utf-8",
        )
        subprocess.run(  # noqa: S603 - fixed platform command and RAGScanner-owned file
            [_program("launchctl"), "bootstrap", f"gui/{os.getuid()}", str(path)], check=False
        )
    elif selected == "win32":
        path.write_text(
            '<Task version="1.4"><RegistrationInfo><Description>RAGScanner local agent</Description>'
            "</RegistrationInfo><Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>"
            '<Principals><Principal id="Author"><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>'
            '<Actions Context="Author"><Exec><Command>'
            f"{sys.executable}</Command><Arguments>-m ragscanner agent run</Arguments>"
            "</Exec></Actions></Task>",
            encoding="utf-8",
        )
        subprocess.run(  # noqa: S603 - fixed platform command and RAGScanner-owned file
            [_program("schtasks"), "/Create", "/TN", AGENT_LABEL, "/XML", str(path), "/F"],
            check=False,
        )
        subprocess.run(  # noqa: S603 - fixed task name
            [_program("schtasks"), "/Run", "/TN", AGENT_LABEL], check=False
        )
    else:
        path.write_text(
            "[Unit]\nDescription=RAGScanner local agent\nAfter=network.target\n\n"
            "[Service]\nType=simple\n"
            f"ExecStart={command}\nRestart=on-failure\nRestartSec=3\n\n"
            "[Install]\nWantedBy=default.target\n",
            encoding="utf-8",
        )
        subprocess.run(  # noqa: S603 - fixed platform command
            [_program("systemctl"), "--user", "daemon-reload"], check=False
        )
        subprocess.run(  # noqa: S603 - fixed service name
            [_program("systemctl"), "--user", "enable", "--now", SERVICE_NAME], check=False
        )
    return path


def remove_autostart(data_dir: Path, *, platform: str | None = None) -> None:
    """Stop and remove only RAGScanner's user-level autostart registration."""
    selected = platform or sys.platform
    path = platform_autostart_path(data_dir, platform=selected)
    if not path.exists():
        return
    if selected == "darwin":
        subprocess.run(  # noqa: S603 - fixed platform command and RAGScanner-owned file
            [_program("launchctl"), "bootout", f"gui/{os.getuid()}", str(path)], check=False
        )
    elif selected == "win32":
        subprocess.run(  # noqa: S603 - fixed task name
            [_program("schtasks"), "/Delete", "/TN", AGENT_LABEL, "/F"], check=False
        )
    else:
        subprocess.run(  # noqa: S603 - fixed service name
            [_program("systemctl"), "--user", "disable", "--now", SERVICE_NAME], check=False
        )
        subprocess.run(  # noqa: S603 - fixed platform command
            [_program("systemctl"), "--user", "daemon-reload"], check=False
        )
    path.unlink(missing_ok=True)


def run_agent(
    database_path: Path,
    *,
    poll_interval: float = 1.0,
    local_administrator_data_dir: Path | None = None,
) -> None:
    """Run the local dashboard/API and one durable worker until interrupted."""
    stop = threading.Event()

    def work() -> None:
        jobs = SQLiteJobRepository(database_path)
        history = SQLiteScanHistoryRepository(database_path)
        schedules = SQLiteScheduleRepository(database_path)
        try:
            worker = DurableWorker(
                jobs,
                {JobKind.SCAN: StaticScanJobHandler(StaticScanApplicationService(history))},
                worker_id=f"agent:{os.getpid()}",
                lease_duration=timedelta(seconds=30),
            )
            while not stop.is_set():
                schedules.materialize_due(jobs)
                if worker.run_once() is None:
                    stop.wait(poll_interval)
        finally:
            schedules.close()
            history.close()
            jobs.close()

    thread = threading.Thread(target=work, name="ragscanner-agent-worker", daemon=True)
    thread.start()
    try:
        uvicorn.run(
            create_app(database_path, local_administrator_data_dir=local_administrator_data_dir),
            host=DASHBOARD_BIND_HOST,
            port=DASHBOARD_PORT,
            access_log=False,
            server_header=False,
        )
    finally:
        stop.set()
        thread.join(timeout=max(2.0, poll_interval * 2))
