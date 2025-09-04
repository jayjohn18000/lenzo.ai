# backend/judge/config.py
from functools import lru_cache
from typing import Literal, List, ClassVar, Dict
import os

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
    MAX_PARALLEL_FANOUT: int = 5

    # Database configuration
    DATABASE_URL: str = Field(default="sqlite:///./nextagi.db", env="DATABASE_URL")

    # Redis configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_DB: int = Field(default=1, env="REDIS_CACHE_DB")

    # Optional: queue and pub/sub names for jobs (safe defaults)
    REDIS_JOB_QUEUE: str = Field(default="jobs:queue", env="REDIS_JOB_QUEUE")
    REDIS_RESULTS_CHANNEL: str = Field(default="jobs:results", env="REDIS_RESULTS_CHANNEL")

    # Toggle: run the worker inside the API process (lifespan) vs. separate process
    RUN_WORKER_IN_PROCESS: bool = Field(default=False, env="RUN_WORKER_IN_PROCESS")

    # Debug mode
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Optional API keys for direct access
    ANTHROPIC_API_KEY: SecretStr = Field(default=SecretStr(""), env="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: SecretStr = Field(default=SecretStr(""), env="OPENAI_API_KEY")

    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")

    # Performance
    ENABLE_CACHING: bool = Field(default=False, env="ENABLE_CACHING")
    ENABLE_BATCH_JUDGING: bool = Field(default=False, env="ENABLE_BATCH_JUDGING")
    MAX_BATCH_SIZE: int = Field(default=8, env="MAX_BATCH_SIZE")

    # Confidence thresholds
    MIN_CACHE_CONFIDENCE: float = Field(default=0.5, env="MIN_CACHE_CONFIDENCE")
    CONF_THRESHOLD: float = Field(default=0.6, env="CONF_THRESHOLD")

    # Model rotation settings
    ENABLE_MODEL_ROTATION: bool = Field(default=True, env="ENABLE_MODEL_ROTATION")

    # Judge model
    JUDGE_MODEL: str = Field(default="openai/gpt-4o-mini", env="JUDGE_MODEL")

    # === Model configurations (static) ===
    DEFAULT_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o-mini",
        "google/gemini-flash-1.5",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3.1-70b-instruct",
        "openai/gpt-4o",
    ]

    SPEED_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "mistralai/mistral-small",
        "google/gemini-flash-1.5",
        "openai/gpt-3.5-turbo",
    ]

    QUALITY_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
    ]

    COST_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku",
        "mistralai/mistral-small",
    ]

    FALLBACK_MODELS: ClassVar[List[str]] = [
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3-70b-instruct",
        "mistralai/mistral-large",
        "cohere/command-r-plus",
    ]

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=(".env", "openrouter_key.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Convenience: headers for OpenRouter calls - PRESERVED ✅
    def openrouter_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key.get_secret_value()}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TruthRouter Local",
        }

    # Derived Redis DSN that prefers REDIS_URL, else builds from host/port/db  ✅
    def redis_dsn(self, db: int | None = None) -> str:
        """
        Returns a redis DSN. If REDIS_URL is set, returns it directly.
        Otherwise constructs: redis://{REDIS_HOST}:{REDIS_PORT}/{db or 0}
        """
        if self.REDIS_URL:
            return self.REDIS_URL
        db_idx = 0 if db is None else int(db)
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{db_idx}"

    # === Back-compat properties - PRESERVED ✅ ===
    @property
    def OPENROUTER_API_KEY(self) -> str:
        return self.openrouter_api_key.get_secret_value()

    @property
    def OPENROUTER_API_URL(self) -> str:
        return str(self.openrouter_api_url)


@lru_cache  # PRESERVED ✅
def get_settings() -> Settings:
    return Settings()


settings = get_settings()  # PRESERVED ✅
