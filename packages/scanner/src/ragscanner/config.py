"""Typed environment configuration with local-only defaults."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ragscanner.paths import default_data_dir


class Settings(BaseSettings):
    """Initial scaffold settings; no remote service is configured or contacted."""

    model_config = SettingsConfigDict(env_prefix="RAGSCANNER_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default_factory=default_data_dir)
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
