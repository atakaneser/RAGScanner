from pathlib import Path

from ragscanner.agent import install_autostart, platform_autostart_path, remove_autostart


def test_linux_user_agent_registration_is_created_and_removed(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "ragscanner.agent.subprocess.run",
        lambda arguments, **kwargs: calls.append(arguments),
    )
    monkeypatch.setattr("ragscanner.agent._program", lambda name: name)

    path = install_autostart(tmp_path / "data", platform="linux")

    assert path == platform_autostart_path(tmp_path / "data", platform="linux")
    content = path.read_text(encoding="utf-8")
    assert "Description=RAGScanner local agent" in content
    assert "-m ragscanner agent run" in content
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", "ragscanner-agent"],
    ]

    remove_autostart(tmp_path / "data", platform="linux")

    assert not path.exists()
    assert calls[-2:] == [
        ["systemctl", "--user", "disable", "--now", "ragscanner-agent"],
        ["systemctl", "--user", "daemon-reload"],
    ]


def test_windows_agent_registration_is_kept_inside_application_data(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "ragscanner.agent.subprocess.run",
        lambda arguments, **kwargs: calls.append(arguments),
    )
    monkeypatch.setattr("ragscanner.agent._program", lambda name: name)

    path = install_autostart(tmp_path / "data", platform="win32")

    assert path == tmp_path / "data" / "agent" / "ragscanner-agent.xml"
    assert "LeastPrivilege" in path.read_text(encoding="utf-8")
    assert calls[0][:3] == ["schtasks", "/Create", "/TN"]
    assert calls[1] == ["schtasks", "/Run", "/TN", "RAGScanner Agent"]
