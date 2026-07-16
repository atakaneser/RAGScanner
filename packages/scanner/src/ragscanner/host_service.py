"""Internal machine-wide service registration used by the unified installer."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from ragscanner.paths import system_data_dir
from ragscanner.version import __version__

SERVICE_NAME = "ragscanner-host"
WINDOWS_SERVICE_NAME = "RAGScannerHost"


def system_runtime_dir(*, platform: str | None = None) -> Path:
    selected = platform or sys.platform
    if selected == "win32":
        return Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "RAGScanner"
    if selected == "darwin":
        return Path("/Library/Application Support/RAGScanner/runtime")
    return Path("/opt/ragscanner")


def machine_launcher_path(*, platform: str | None = None) -> Path:
    selected = platform or sys.platform
    suffix = ".exe" if selected == "win32" else ""
    return system_runtime_dir(platform=selected) / "bin" / f"ragscanner{suffix}"


def _program(name: str) -> str:
    return shutil.which(name) or name


def _installation_source() -> str:
    override = os.environ.get("RAGSCANNER_INSTALL_SOURCE", "").strip()
    if override:
        return override
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return str(parent)
    try:
        direct_url = metadata.distribution("ragscanner").read_text("direct_url.json")
        parsed = json.loads(direct_url) if direct_url else {}
        url = parsed.get("url")
        if isinstance(url, str) and url.strip():
            return url
    except (json.JSONDecodeError, metadata.PackageNotFoundError):
        pass
    return f"ragscanner=={__version__}"


def install_machine_runtime(*, platform: str | None = None, reinstall: bool = False) -> Path:
    """Install an isolated executable runtime outside every user profile."""

    selected = platform or sys.platform
    runtime = system_runtime_dir(platform=selected)
    bin_dir = runtime / "bin"
    tool_dir = runtime / "tools"
    bin_dir.mkdir(parents=True, exist_ok=True)
    tool_dir.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv is None:
        raise OSError("uv is required to create the machine-wide RAGScanner runtime")
    arguments = [uv, "tool", "install", "--force", _installation_source()]
    if reinstall:
        arguments.insert(-1, "--reinstall")
    environment = os.environ.copy()
    environment.update({"UV_TOOL_DIR": str(tool_dir), "UV_TOOL_BIN_DIR": str(bin_dir)})
    result = subprocess.run(arguments, check=False, env=environment)  # noqa: S603
    if result.returncode != 0 or not machine_launcher_path(platform=selected).is_file():
        raise OSError("machine-wide RAGScanner runtime installation failed")
    return machine_launcher_path(platform=selected)


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
    launcher = install_machine_runtime(platform=selected)
    command = f'"{launcher}" host run --data-dir "{data_dir}"'
    if selected == "win32":
        definition.write_text(command + "\n", encoding="utf-8")
        created = subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned command
            [
                _program("sc.exe"),
                "create",
                WINDOWS_SERVICE_NAME,
                f"binPath= {command}",
                "start= auto",
                "obj= LocalSystem",
            ],
            check=False,
        )
        if getattr(created, "returncode", 0) != 0:
            subprocess.run(  # noqa: S603 - idempotently update the product-owned service
                [
                    _program("sc.exe"),
                    "config",
                    WINDOWS_SERVICE_NAME,
                    f"binPath= {command}",
                    "start= auto",
                    "obj= LocalSystem",
                ],
                check=False,
            )
        subprocess.run(  # noqa: S603 - fixed Windows service utility and product-owned service
            [_program("sc.exe"), "start", WINDOWS_SERVICE_NAME], check=False
        )
        verified = subprocess.run(  # noqa: S603 - fixed product-owned service query
            [_program("sc.exe"), "query", WINDOWS_SERVICE_NAME], check=False
        )
        if getattr(verified, "returncode", 0) != 0:
            raise OSError("Windows Host Service registration could not be verified")
        return definition
    if selected == "darwin":
        definition.parent.mkdir(parents=True, exist_ok=True)
        definition.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict><key>Label</key><string>com.ragscanner.host</string>'
            f"<key>ProgramArguments</key><array><string>{launcher}</string>"
            "<string>host</string><string>run</string><string>--data-dir</string>"
            f"<string>{data_dir}</string></array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
            "</dict></plist>\n",
            encoding="utf-8",
        )
        subprocess.run(  # noqa: S603 - remove an older product-owned registration if present
            [_program("launchctl"), "bootout", "system/com.ragscanner.host"], check=False
        )
        registered = subprocess.run(  # noqa: S603 - fixed platform utility and product-owned plist
            [_program("launchctl"), "bootstrap", "system", str(definition)], check=False
        )
        if getattr(registered, "returncode", 0) != 0:
            raise OSError("macOS Host Service registration failed")
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
    reloaded = subprocess.run(  # noqa: S603 - fixed platform utility
        [_program("systemctl"), "daemon-reload"], check=False
    )
    started = subprocess.run(  # noqa: S603 - fixed service name
        [_program("systemctl"), "enable", "--now", SERVICE_NAME], check=False
    )
    if getattr(reloaded, "returncode", 0) != 0 or getattr(started, "returncode", 0) != 0:
        raise OSError("Linux Host Service registration failed")
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


def restart_host_service(*, platform: str | None = None) -> None:
    """Restart the registered machine service after a runtime replacement."""

    selected = platform or sys.platform
    if selected == "win32":
        subprocess.run([_program("sc.exe"), "stop", WINDOWS_SERVICE_NAME], check=False)  # noqa: S603
        subprocess.run([_program("sc.exe"), "start", WINDOWS_SERVICE_NAME], check=False)  # noqa: S603
    elif selected == "darwin":
        subprocess.run(  # noqa: S603
            [_program("launchctl"), "kickstart", "-k", "system/com.ragscanner.host"],
            check=False,
        )
    else:
        subprocess.run([_program("systemctl"), "restart", SERVICE_NAME], check=False)  # noqa: S603


def remove_machine_runtime(*, platform: str | None = None) -> None:
    """Remove the machine runtime, deferring Windows deletion until process exit."""

    selected = platform or sys.platform
    runtime = system_runtime_dir(platform=selected)
    if selected != "win32":
        shutil.rmtree(runtime, ignore_errors=True)
        return
    data_dir = system_data_dir(platform=selected)
    data_dir.mkdir(parents=True, exist_ok=True)
    script = data_dir / "remove-runtime.cmd"
    script.write_text(
        f'@echo off\r\nping 127.0.0.1 -n 4 > nul\r\nrmdir /s /q "{runtime}"\r\ndel "%~f0"\r\n',
        encoding="utf-8",
    )
    subprocess.Popen(  # noqa: S603 - fixed local cleanup script
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(script)],
        close_fds=True,
        creationflags=(
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        ),
    )
