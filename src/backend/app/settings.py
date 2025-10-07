from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    database_url: str = "sqlite:///data/open_data_insight.db"
    openai_api_key: SecretStr | None = None
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Origins allowed to call the API",
    )

    model_config = SettingsConfigDict(
        env_prefix="OPEN_DATA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            if not value.strip():
                return []
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if value is None:
            return []
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
