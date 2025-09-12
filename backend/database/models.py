# backend/database/models.py
"""Analytics database models for NextAGI (SQLAlchemy 2.x style)."""

from __future__ import annotations

from datetime import datetime
import json
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


# -----------------------------------------------------
# SQLAlchemy 2.x Declarative Base for ANALYTICS models
# -----------------------------------------------------
class AnalyticsBase(DeclarativeBase):
    """Dedicated Base for analytics persistence models."""

    pass


# For external imports (e.g., create_all() in main)
Base = AnalyticsBase


class QueryRequest(Base):
    """Store each query request for analytics."""

    __tablename__ = "query_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[Optional[str]] = mapped_column(
        String(20)
    )  # speed, quality, balanced, cost
    max_models: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    total_cost: Mapped[Optional[float]] = mapped_column(Float)
    winner_confidence: Mapped[Optional[float]] = mapped_column(Float)
    winner_model: Mapped[Optional[str]] = mapped_column(String(100))
    models_used_json: Mapped[Optional[str]] = mapped_column(
        Text
    )  # JSON array of model names

    # Relationships
    model_responses: Mapped[List["ModelResponse"]] = relationship(
        back_populates="query_request",
        cascade="all, delete-orphan",
    )

    # Convenience accessors for models_used
    @property
    def models_used(self) -> List[str]:
        return json.loads(self.models_used_json) if self.models_used_json else []

    @models_used.setter
    def models_used(self, value: List[str]) -> None:
        self.models_used_json = json.dumps(value)


class ModelResponse(Base):
    """Store individual model responses for analysis."""

    __tablename__ = "model_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("query_requests.request_id")
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(100))
    response_text: Mapped[Optional[str]] = mapped_column(Text)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)  # Must be 0-1
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    cost: Mapped[Optional[float]] = mapped_column(Float)
    reliability_score: Mapped[Optional[float]] = mapped_column(Float)
    consistency_score: Mapped[Optional[float]] = mapped_column(Float)
    hallucination_risk: Mapped[Optional[float]] = mapped_column(Float)
    citation_quality: Mapped[Optional[float]] = mapped_column(Float)
    rank_position: Mapped[Optional[int]] = mapped_column(Integer)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Store trait scores as JSON (string)
    trait_scores_json: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship
    query_request: Mapped["QueryRequest"] = relationship(
        back_populates="model_responses"
    )

    @property
    def trait_scores(self) -> Dict[str, Any]:
        return json.loads(self.trait_scores_json) if self.trait_scores_json else {}

    @trait_scores.setter
    def trait_scores(self, value: Dict[str, Any]) -> None:
        self.trait_scores_json = json.dumps(value)


# -----------------------------
# Database helpers (optional)
# -----------------------------
def init_db(database_url: str = "sqlite:///nextagi.db"):
    """
    Initialize the analytics database with tables and return the engine.

    Note: This helper is optional; many apps will manage engine/session
    elsewhere and simply call `Base.metadata.create_all(engine)`.
    """
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session bound to the provided engine."""
    Session = sessionmaker(bind=engine, future=True)
    return Session()
