from subprocess import CompletedProcess

import pytest
from ragscanner.host_service import (
    install_host_service,
    machine_launcher_path,
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
    assert [call[1] for call in task_calls] == ["/Create", "/Run", "/Query"]
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
    monkeypatch.setattr("ragscanner.host_service.subprocess.run", run)

    with pytest.raises(OSError, match="Windows Host task registration failed with exit code 5"):
        install_host_service(platform="win32")

    assert [call[1] for call in calls] == ["stop", "delete", "/Create"]
    assert not definition.exists()


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
