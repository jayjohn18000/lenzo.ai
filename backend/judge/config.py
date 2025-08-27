# backend/judge/config.py
from functools import lru_cache
from typing import Literal, List
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

    # ===== ADD THESE MISSING PROPERTIES =====
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./nextagi.db",
        env="DATABASE_URL"
    )
    
    # Redis configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Debug mode
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Optional API keys for direct access
    ANTHROPIC_API_KEY: SecretStr = Field(default="", env="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: SecretStr = Field(default="", env="OPENAI_API_KEY")
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    
    # ===== END ADDITIONS =====
        # Caching

    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_CACHE_DB = 1

    # Performance
    ENABLE_CACHING=False
    ENABLE_BATCH_JUDGING=False
    MAX_BATCH_SIZE = 8

    # Confidence thresholds
    MIN_CACHE_CONFIDENCE = 0.7
    CONF_THRESHOLD = 0.85

    # === Model configurations based on test results ===
    # Primary models: Fast, reliable, diverse providers
    DEFAULT_MODELS: List[str] = [
        "openai/gpt-4o-mini",           # Fastest OpenAI, cost-effective
        "google/gemini-flash-1.5",      # Second fastest overall  
        "anthropic/claude-3-haiku",     # Fast Anthropic option
        "meta-llama/llama-3.1-70b-instruct",  # Fast open-source option
        "openai/gpt-4o",                # Premium option for quality
    ]
    
    # Alternative model sets for different use cases
    SPEED_OPTIMIZED_MODELS: List[str] = [
        "mistralai/mistral-small",      # 0.48s - fastest
        "google/gemini-flash-1.5",      # 0.55s - second fastest
        "openai/gpt-3.5-turbo",         # 0.62s - reliable and fast
    ]
    
    QUALITY_OPTIMIZED_MODELS: List[str] = [
        "openai/gpt-4o",                # Premium quality
        "anthropic/claude-3.5-sonnet",  # Top Anthropic model
        "anthropic/claude-3-opus",      # Highest quality Anthropic
    ]
    
    COST_OPTIMIZED_MODELS: List[str] = [
        "openai/gpt-4o-mini",           # Cheapest OpenAI
        "anthropic/claude-3-haiku",     # Cheapest Anthropic
        "mistralai/mistral-small",      # Fast and cost-effective
    ]
    
    # Judge model - use reliable, fast model for evaluation
    JUDGE_MODEL: str = "openai/gpt-4o-mini"  # Fast and reliable for judging
    
    # Confidence threshold for escalation
    CONF_THRESHOLD: float = 0.85

    # === Model rotation settings ===
    # You can enable model rotation to distribute load and avoid rate limits
    ENABLE_MODEL_ROTATION: bool = True
    
    # Fallback models if primary models fail
    FALLBACK_MODELS: List[str] = [
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3-70b-instruct", 
        "mistralai/mistral-large",
        "cohere/command-r-plus"
    ]

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