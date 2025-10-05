from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    database_url: str = "sqlite:///data/open_data_insight.db"
    openai_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_prefix="OPEN_DATA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
