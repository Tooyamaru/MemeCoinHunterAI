"""Typed, environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime configuration with safe development defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Environment = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_version: str = "0.1.0"
    database_url: str | None = None
    log_level: LogLevel = "INFO"
    operator_bearer_token: str | None = None
    operator_case_registry_capacity: int = Field(default=64, ge=1, le=4096)
    operator_case_ttl_seconds: int = Field(default=1800, ge=1, le=86400)
    solana_rpc_url: str | None = None
    solana_rpc_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    solana_rpc_max_response_bytes: int = Field(default=262144, ge=1024, le=1048576)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings object."""

    return Settings()
