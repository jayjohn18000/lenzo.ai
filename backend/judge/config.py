# backend/judge/config.py

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Required secrets / keys
    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")

    # App config (optional but handy)
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    request_timeout_seconds: float = 60.0

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=(".env", "openrouter_key.env"),  # load from either if present
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Helper for auth headers when calling OpenRouter
    def openrouter_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key.get_secret_value()}",
            # Optional but recommended by OpenRouter:
            # Set these to something meaningful for your app / domain
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TruthRouter Local",
        }


@lru_cache
def get_settings() -> Settings:
    # Cached singleton so we don't re-parse env on every import
    return Settings()


# Convenient module-level instance if you prefer `from ... import settings`
settings = get_settings()
