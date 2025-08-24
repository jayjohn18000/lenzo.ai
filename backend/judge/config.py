# backend/judge/config.py
"""
Complete working configuration for NextAGI with enhanced async processing
"""
from functools import lru_cache
from typing import Literal, List, Dict
from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === Core API Configuration ===
    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_api_url: HttpUrl = Field("https://openrouter.ai/api/v1", alias="OPENROUTER_API_URL")
    
    # === App Settings ===
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    request_timeout_seconds: float = 60.0
    MAX_PARALLEL_FANOUT: int = 5

    # === Model Configurations ===
    DEFAULT_MODELS: List[str] = [
        "openai/gpt-4o-mini",           # Fastest OpenAI, cost-effective
        "google/gemini-flash-1.5",      # Second fastest overall  
        "anthropic/claude-3-haiku",     # Fast Anthropic option
        "meta-llama/llama-3.1-70b-instruct",  # Fast open-source option
        "openai/gpt-4o",                # Premium option for quality
    ]
    
    # Enhanced model sets for different modes
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
    
    FALLBACK_MODELS: List[str] = [
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3-70b-instruct", 
        "mistralai/mistral-large",
        "cohere/command-r-plus"
    ]
    
    # === Judge Configuration ===
    JUDGE_MODEL: str = "openai/gpt-4o-mini"
    CONF_THRESHOLD: float = 0.85

    # === Enhanced Async Settings ===
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME: int = 120
    ENABLE_MODEL_ROTATION: bool = True
    
    # === Performance Timeouts ===
    MODEL_TIMEOUTS: Dict[str, float] = {
        "anthropic/claude-3-opus": 35.0,
        "meta-llama/llama-3.1-405b-instruct": 40.0, 
        "google/gemini-1.5-pro": 30.0,
        "openai/gpt-4o-mini": 15.0,
        "anthropic/claude-3-haiku": 15.0,
        "google/gemini-flash-1.5": 15.0,
    }

    # === Optional Enhanced Settings ===
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./nextagi.db"
    PIPELINE_TIMEOUT_SECONDS: float = 30.0

    # === Pydantic Configuration ===
    model_config = SettingsConfigDict(
        env_file=(".env", "openrouter_key.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === Core Methods ===
    def openrouter_headers(self) -> dict:
        """Generate headers for OpenRouter API calls"""
        return {
            "Authorization": f"Bearer {self.openrouter_api_key.get_secret_value()}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "NextAGI Enhanced",
            "Content-Type": "application/json"
        }

    # === Back-compatibility Properties ===
    @property
    def OPENROUTER_API_KEY(self) -> str:
        return self.openrouter_api_key.get_secret_value()

    @property
    def OPENROUTER_API_URL(self) -> str:
        return str(self.openrouter_api_url)

    # === REQUIRED METHODS for Enhanced Judge Pipeline ===
    def get_models_for_mode(self, mode: str) -> List[str]:
        """Get optimized model list for the specified mode"""
        if mode == "speed":
            return self.SPEED_OPTIMIZED_MODELS
        elif mode == "quality":  
            return self.QUALITY_OPTIMIZED_MODELS
        elif mode == "cost":
            return self.COST_OPTIMIZED_MODELS
        else:  # balanced
            return self.DEFAULT_MODELS
    
    def get_model_timeout(self, model: str) -> float:
        """Get timeout for specific model, with fallback to default"""
        return self.MODEL_TIMEOUTS.get(model, self.request_timeout_seconds)
    
    def get_max_concurrent_for_mode(self, mode: str) -> int:
        """Get maximum concurrent requests for the specified mode"""
        if mode == "speed":
            return min(self.MAX_PARALLEL_FANOUT + 2, 8)
        elif mode == "quality": 
            return max(self.MAX_PARALLEL_FANOUT - 1, 2)
        else:
            return self.MAX_PARALLEL_FANOUT
    
    # === Additional Helper Methods ===
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "prod"
    
    def get_all_available_models(self) -> List[str]:
        """Get all configured models"""
        all_models = set()
        all_models.update(self.DEFAULT_MODELS)
        all_models.update(self.SPEED_OPTIMIZED_MODELS)
        all_models.update(self.QUALITY_OPTIMIZED_MODELS)
        all_models.update(self.COST_OPTIMIZED_MODELS)
        all_models.update(self.FALLBACK_MODELS)
        return list(all_models)
    
    def validate_model(self, model: str) -> bool:
        """Check if a model is in our configured model lists"""
        return model in self.get_all_available_models()


@lru_cache()
def get_settings() -> Settings:
    """Get settings instance (cached singleton)"""
    return Settings()


# Global settings instance - NO CIRCULAR IMPORT
settings = get_settings()


# === Configuration Validation ===
def validate_configuration():
    """Validate critical configuration settings"""
    errors = []
    warnings = []
    
    try:
        # Check required API keys
        if not settings.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required")
        
        # Validate model lists
        if not settings.DEFAULT_MODELS:
            errors.append("DEFAULT_MODELS cannot be empty")
        
        if not settings.SPEED_OPTIMIZED_MODELS:
            warnings.append("SPEED_OPTIMIZED_MODELS is empty")
        
        # Validate timeout settings
        if settings.request_timeout_seconds <= 0:
            errors.append("REQUEST_TIMEOUT_SECONDS must be positive")
        
        if settings.PIPELINE_TIMEOUT_SECONDS <= settings.request_timeout_seconds:
            warnings.append("PIPELINE_TIMEOUT_SECONDS should be greater than REQUEST_TIMEOUT_SECONDS")
        
        # Validate parallel processing settings
        if settings.MAX_PARALLEL_FANOUT <= 0:
            errors.append("MAX_PARALLEL_FANOUT must be positive")
        
        if settings.MAX_PARALLEL_FANOUT > 10:
            warnings.append("MAX_PARALLEL_FANOUT > 10 may cause rate limiting issues")
        
        # Log results
        if errors:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Configuration errors: {'; '.join(errors)}")
            
        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Configuration warnings: {'; '.join(warnings)}")
            
        return len(errors) == 0
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Configuration validation failed: {e}")
        return False


# Validate configuration on import (with error handling)
try:
    is_valid = validate_configuration()
    if not is_valid:
        import logging
        logging.getLogger(__name__).warning("Configuration validation failed - some features may not work correctly")
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"Could not validate configuration: {e}")


# === Export commonly used items ===
__all__ = ["settings", "get_settings", "validate_configuration"]