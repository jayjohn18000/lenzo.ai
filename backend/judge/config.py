# backend/judge/config.py
from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === Required secrets / keys ===
    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")

    # === API base URL (default to OpenRouter's public API) ===
    openrouter_api_url: HttpUrl = Field(
        "https://openrouter.ai/api/v1",
        alias="OPENROUTER_API_URL",
    )

    # === App config ===
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    request_timeout_seconds: float = 60.0
    MAX_PARALLEL_FANOUT: int = 5  # default value

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=(".env", "openrouter_key.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Convenience: headers for OpenRouter calls
    def openrouter_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key.get_secret_value()}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TruthRouter Local",
        }

    # === Back-compat properties ===
    # Allow old code that accesses UPPERCASE names to keep working.
    @property
    def OPENROUTER_API_KEY(self) -> str:
        return self.openrouter_api_key.get_secret_value()

    @property
    def OPENROUTER_API_URL(self) -> str:
        return str(self.openrouter_api_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
