from ragscanner.host_service import service_definition_path, system_data_dir


def test_host_service_uses_machine_owned_paths() -> None:
    assert system_data_dir(platform="linux").as_posix() == "/var/lib/ragscanner"
    assert (
        service_definition_path(platform="linux").as_posix()
        == "/etc/systemd/system/ragscanner-host.service"
    )
    assert (
        service_definition_path(platform="darwin").as_posix()
        == "/Library/LaunchDaemons/com.ragscanner.host.plist"
    )


def test_windows_host_service_definition_is_kept_under_program_data(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ProgramData", r"D:\\ProgramData")

    assert system_data_dir(platform="win32") == service_definition_path(platform="win32").parent
