# backend/judge/config.py
from functools import lru_cache
from typing import Literal, List, ClassVar
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

    # ===== FIXED: ADD TYPE ANNOTATIONS TO ALL FIELDS =====
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./nextagi.db",
        env="DATABASE_URL"
    )
    
    # Redis configuration - FIXED: Added type annotations
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT") 
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_DB: int = Field(default=1, env="REDIS_CACHE_DB")  # FIXED: Added type annotation
    
    # Debug mode
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Optional API keys for direct access
    ANTHROPIC_API_KEY: SecretStr = Field(default="", env="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: SecretStr = Field(default="", env="OPENAI_API_KEY")
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    
    # Performance - FIXED: Added type annotations
    ENABLE_CACHING: bool = Field(default=False, env="ENABLE_CACHING")
    ENABLE_BATCH_JUDGING: bool = Field(default=False, env="ENABLE_BATCH_JUDGING") 
    MAX_BATCH_SIZE: int = Field(default=8, env="MAX_BATCH_SIZE")

    # Confidence thresholds - FIXED: Added type annotations
    MIN_CACHE_CONFIDENCE: float = Field(default=0.7, env="MIN_CACHE_CONFIDENCE")
    CONF_THRESHOLD: float = Field(default=0.85, env="CONF_THRESHOLD")  # Single definition

    # Model rotation settings - FIXED: Added type annotations
    ENABLE_MODEL_ROTATION: bool = Field(default=True, env="ENABLE_MODEL_ROTATION")
    
    # Judge model - FIXED: Added type annotation
    JUDGE_MODEL: str = Field(default="openai/gpt-4o-mini", env="JUDGE_MODEL")

    # === Model configurations based on test results - FIXED: Use ClassVar ===
    # Primary models: Fast, reliable, diverse providers
    DEFAULT_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o-mini",           # Fastest OpenAI, cost-effective
        "google/gemini-flash-1.5",      # Second fastest overall  
        "anthropic/claude-3-haiku",     # Fast Anthropic option
        "meta-llama/llama-3.1-70b-instruct",  # Fast open-source option
        "openai/gpt-4o",                # Premium option for quality
    ]
    
    # Alternative model sets for different use cases
    SPEED_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "mistralai/mistral-small",      # 0.48s - fastest
        "google/gemini-flash-1.5",      # 0.55s - second fastest
        "openai/gpt-3.5-turbo",         # 0.62s - reliable and fast
    ]
    
    QUALITY_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o",                # Premium quality
        "anthropic/claude-3.5-sonnet",  # Top Anthropic model
        "anthropic/claude-3-opus",      # Highest quality Anthropic
    ]
    
    COST_OPTIMIZED_MODELS: ClassVar[List[str]] = [
        "openai/gpt-4o-mini",           # Cheapest OpenAI
        "anthropic/claude-3-haiku",     # Cheapest Anthropic
        "mistralai/mistral-small",      # Fast and cost-effective
    ]
    
    # Fallback models if primary models fail
    FALLBACK_MODELS: ClassVar[List[str]] = [
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

    # Convenience: headers for OpenRouter calls - PRESERVED ✅
    def openrouter_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key.get_secret_value()}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TruthRouter Local",
        }

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