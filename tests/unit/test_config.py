from pathlib import Path

from ragscanner.config import Settings


def test_environment_configuration(monkeypatch) -> None:
    monkeypatch.setenv("RAGSCANNER_DATA_DIR", ".test-data")
    monkeypatch.setenv("RAGSCANNER_LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.data_dir == Path(".test-data")
    assert settings.log_level == "DEBUG"
