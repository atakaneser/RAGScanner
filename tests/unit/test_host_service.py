from ragscanner.host_service import (
    install_host_service,
    machine_launcher_path,
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
    assert str(system_runtime_dir(platform="win32")).startswith(r"C:\\Program Files")


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
