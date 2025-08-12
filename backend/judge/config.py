# backend/judge/config.py
import os
from pydantic import BaseSettings, Field
from typing import List

class Settings(BaseSettings):
    # --- Provider keys / endpoints ---
    OPENROUTER_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))

    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_HEADERS: dict = Field(
        default_factory=lambda: {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}",
            # Helpful but optional meta headers for OpenRouter
            "HTTP-Referer": os.getenv("HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("APP_TITLE", "TruthRouter"),
            "Content-Type": "application/json",
        }
    )

    # --- Routing & scoring policy ---
    CONF_THRESHOLD: float = 0.85            # escalate to tool_chain if pre-pass falls below this
    CITATIONS_DEFAULT_ON: bool = True       # keep citations on for both pipelines

    # --- Model selections ---
    DEFAULT_MODELS: List[str] = [
        "openrouter/anthropic/claude-3.5-sonnet",
        "openrouter/openai/gpt-4o",
        "openrouter/mistralai/mistral-large",
    ]
    JUDGE_MODEL: str = "openrouter/openai/gpt-4o-mini"

    # --- Time & cost guards (simple MVP knobs) ---
    HARD_TIME_BUDGET_SEC: float = 20.0
    SOFT_TIME_BUDGET_SEC: float = 8.0
    MAX_PARALLEL_FANOUT: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
