from pathlib import Path
from subprocess import CompletedProcess

import pytest
from ragscanner.host_service import (
    DEFAULT_UPDATE_SOURCE,
    _updated_windows_machine_path,
    install_host_service,
    install_machine_command,
    install_machine_runtime,
    machine_command_path,
    machine_launcher_path,
    remove_machine_command,
    restart_host_service,
    service_definition_path,
    system_data_dir,
    system_runtime_dir,
)


def test_host_service_uses_machine_owned_paths() -> None:
    assert system_data_dir(platform="linux").as_posix() == "/var/lib/ragscanner"
    assert (
        service_definition_path(platform="linux").as_posix()
        == "/etc/systemd/system/ragscanner-host.service"
    )
    assert system_runtime_dir(platform="linux").as_posix() == "/opt/ragscanner"
    assert machine_launcher_path(platform="linux").as_posix() == "/opt/ragscanner/bin/ragscanner"
    assert (
        service_definition_path(platform="darwin").as_posix()
        == "/Library/LaunchDaemons/com.ragscanner.host.plist"
    )


def test_windows_host_service_definition_is_kept_under_program_data(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ProgramData", r"D:\\ProgramData")

    assert system_data_dir(platform="win32") == service_definition_path(platform="win32").parent
    assert service_definition_path(platform="win32").name == "host-task.xml"
    assert str(system_runtime_dir(platform="win32")).startswith(r"C:\\Program Files")


def test_windows_host_uses_boot_task_running_as_local_system(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    definition = tmp_path / "host-task.xml"
    data_dir = tmp_path / "machine & data"
    launcher = tmp_path / "runtime & tools" / "ragscanner.exe"
    calls: list[list[str]] = []

    def run(arguments, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(arguments)
        return CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr("ragscanner.host_service.is_elevated", lambda **kwargs: True)
    monkeypatch.setattr("ragscanner.host_service.system_data_dir", lambda **kwargs: data_dir)
    monkeypatch.setattr(
        "ragscanner.host_service.service_definition_path", lambda **kwargs: definition
    )
    monkeypatch.setattr(
        "ragscanner.host_service.install_machine_runtime", lambda **kwargs: launcher
    )
    monkeypatch.setattr(
        "ragscanner.host_service.install_machine_command", lambda *args, **kwargs: launcher
    )
    monkeypatch.setattr("ragscanner.host_service.subprocess.run", run)

    assert install_host_service(platform="win32") == definition

    raw_definition = definition.read_bytes()
    assert raw_definition.startswith(b"\xff\xfe")
    contents = raw_definition.decode("utf-16")
    assert contents.startswith('<?xml version="1.0" encoding="UTF-16"?>\r\n')
    assert "<BootTrigger>" in contents
    assert "<UserId>S-1-5-18</UserId>" in contents
    assert "<LogonType>" not in contents
    assert "<RestartOnFailure>" in contents
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in contents
    assert "runtime &amp; tools" in contents
    assert "machine &amp; data" in contents
    task_calls = [call for call in calls if call[0].endswith("schtasks.exe")]
    assert [call[1] for call in task_calls] == ["/Create", "/End", "/Run", "/Query"]
    assert [call[1] for call in calls[:2]] == ["stop", "delete"]


def test_windows_host_registration_failure_stops_before_start(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    definition = tmp_path / "host-task.xml"
    data_dir = tmp_path / "data"
    launcher = tmp_path / "ragscanner.exe"
    calls: list[list[str]] = []

    def run(arguments, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(arguments)
        return CompletedProcess(arguments, 5, "", "Access is denied")

    monkeypatch.setattr("ragscanner.host_service.is_elevated", lambda **kwargs: True)
    monkeypatch.setattr("ragscanner.host_service.system_data_dir", lambda **kwargs: data_dir)
    monkeypatch.setattr(
        "ragscanner.host_service.service_definition_path", lambda **kwargs: definition
    )
    monkeypatch.setattr(
        "ragscanner.host_service.install_machine_runtime", lambda **kwargs: launcher
    )
    monkeypatch.setattr(
        "ragscanner.host_service.install_machine_command", lambda *args, **kwargs: launcher
    )
    monkeypatch.setattr("ragscanner.host_service.subprocess.run", run)

    with pytest.raises(OSError, match="Windows Host task registration failed with exit code 5"):
        install_host_service(platform="win32")

    assert [call[1] for call in calls] == ["stop", "delete", "/Create"]
    assert not definition.exists()


def test_windows_machine_command_follows_the_active_generation(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    runtime = tmp_path / "runtime"
    launcher = runtime / "generations" / ("a" * 32) / "bin" / "ragscanner.exe"
    path_changes: list[tuple[Path, bool]] = []
    monkeypatch.setattr("ragscanner.host_service.system_runtime_dir", lambda **kwargs: runtime)
    monkeypatch.setattr(
        "ragscanner.host_service._write_windows_machine_path",
        lambda path, remove=False: path_changes.append((path, remove)),
    )

    command = install_machine_command(launcher, platform="win32")

    assert command == machine_command_path(platform="win32")
    contents = command.read_text(encoding="utf-8")
    assert "current-generation.txt" in contents
    assert "%RAGSCANNER_GENERATION%" in contents
    assert 'ragscanner.exe" %*' in contents
    assert path_changes == [(command.parent, False)]

    remove_machine_command(platform="win32")

    assert not command.exists()
    assert path_changes[-1] == (command.parent, True)


def test_windows_machine_path_is_idempotent_and_preserves_other_entries() -> None:
    command_dir = Path(r"C:\Program Files\RAGScanner\command")
    original = r"C:\Windows\System32;C:\Tools"
    added = _updated_windows_machine_path(original, command_dir)

    assert added == original + ";" + str(command_dir)
    assert _updated_windows_machine_path(added + "\\", command_dir) == added
    assert _updated_windows_machine_path(added, command_dir, remove=True) == original


def test_windows_runtime_upgrade_installs_a_new_generation_from_github(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    runtime = tmp_path / "runtime"
    calls: list[tuple[list[str], dict[str, str]]] = []

    def run(arguments, **kwargs):  # type: ignore[no-untyped-def]
        environment = kwargs["env"]
        calls.append((arguments, environment))
        launcher = Path(environment["UV_TOOL_BIN_DIR"]) / "ragscanner.exe"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.touch()
        return CompletedProcess(arguments, 0)

    monkeypatch.setattr("ragscanner.host_service.system_runtime_dir", lambda **kwargs: runtime)
    monkeypatch.setattr("ragscanner.host_service.shutil.which", lambda name: "uv")
    monkeypatch.setattr("ragscanner.host_service.subprocess.run", run)
    monkeypatch.setattr(
        "ragscanner.host_service.uuid4", lambda: type("ID", (), {"hex": "a" * 32})()
    )

    launcher = install_machine_runtime(platform="win32", upgrade=True)

    assert launcher == runtime / "generations" / ("a" * 32) / "bin" / "ragscanner.exe"
    assert machine_launcher_path(platform="win32") == launcher
    assert calls[0][0] == ["uv", "tool", "install", "--force", "--upgrade", DEFAULT_UPDATE_SOURCE]
    assert calls[0][1]["UV_TOOL_DIR"] == str(launcher.parent.parent / "tools")


def test_windows_runtime_failure_keeps_current_generation(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    runtime = tmp_path / "runtime"
    current = "b" * 32
    (runtime / "generations" / current / "bin").mkdir(parents=True)
    existing_launcher = runtime / "generations" / current / "bin" / "ragscanner.exe"
    existing_launcher.touch()
    (runtime / "current-generation.txt").write_text(current, encoding="ascii")
    monkeypatch.setattr("ragscanner.host_service.system_runtime_dir", lambda **kwargs: runtime)
    monkeypatch.setattr("ragscanner.host_service.shutil.which", lambda name: "uv")
    monkeypatch.setattr(
        "ragscanner.host_service.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(args[0], 1),
    )
    monkeypatch.setattr(
        "ragscanner.host_service.uuid4", lambda: type("ID", (), {"hex": "c" * 32})()
    )

    with pytest.raises(OSError, match="runtime installation failed"):
        install_machine_runtime(platform="win32", upgrade=True)

    assert machine_launcher_path(platform="win32") == existing_launcher
    assert not (runtime / "generations" / ("c" * 32)).exists()


def test_windows_host_restart_uses_the_machine_task(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []

    def run(arguments, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(arguments)
        return CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr("ragscanner.host_service.subprocess.run", run)

    restart_host_service(platform="win32")

    assert [call[1] for call in calls] == ["/End", "/Run"]


def test_macos_service_uses_the_isolated_machine_launcher(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    definition = tmp_path / "com.ragscanner.host.plist"
    data_dir = tmp_path / "data"
    launcher = tmp_path / "runtime" / "bin" / "ragscanner"
    launcher.parent.mkdir(parents=True)
    launcher.touch()
    monkeypatch.setattr("ragscanner.host_service.is_elevated", lambda **kwargs: True)
    monkeypatch.setattr("ragscanner.host_service.system_data_dir", lambda **kwargs: data_dir)
    monkeypatch.setattr(
        "ragscanner.host_service.service_definition_path", lambda **kwargs: definition
    )
    monkeypatch.setattr(
        "ragscanner.host_service.install_machine_runtime", lambda **kwargs: launcher
    )
    monkeypatch.setattr("ragscanner.host_service.subprocess.run", lambda *args, **kwargs: None)

    installed = install_host_service(platform="darwin")

    contents = installed.read_text(encoding="utf-8")
    assert f"<string>{launcher}</string>" in contents
    assert "<string>-m</string>" not in contents
