from pathlib import Path

from ragscanner.config import Settings


def test_environment_configuration(monkeypatch) -> None:
    monkeypatch.setenv("RAGSCANNER_DATA_DIR", ".test-data")
    monkeypatch.setenv("RAGSCANNER_LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.data_dir == Path(".test-data")
    assert settings.log_level == "DEBUG"


def test_default_data_directory_is_platform_native_and_not_working_directory(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("RAGSCANNER_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = Settings(_env_file=None)

    assert settings.data_dir.is_absolute()
    assert settings.data_dir != tmp_path / ".ragscanner"
