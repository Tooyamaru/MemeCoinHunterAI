"""Typed, environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime configuration with safe development defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Environment = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_version: str = "0.1.0"
    database_url: str | None = None
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings object."""

    return Settings()
