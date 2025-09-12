# backend/jobs/models.py
from __future__ import annotations

"""
Job datamodels for the async pipeline.

- QueryJob: an in-memory dataclass used by the worker to run the pipeline.
- JobRecord: SQLAlchemy 2.x ORM model for optional DB persistence.
- JobStatus: str/Enum whose values match the Redis contract exactly.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import logging

from sqlalchemy import String, Text, Integer, Float, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions

logger = logging.getLogger(__name__)


# -----------------------------------------------------
# SQLAlchemy 2.x Declarative Base for JOBS persistence
# -----------------------------------------------------
class JobsBase(DeclarativeBase):
    """Dedicated Base for job persistence models."""

    pass


# For external imports (e.g., create_all() in main)
Base = JobsBase


class JobStatus(str, Enum):
    """Lifecycle values must match Redis string values exactly."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# -------------------------------
# Optional ORM row for persistence
# -------------------------------
class JobRecord(Base):  # type: ignore[misc]
    """
    ORM table for persisted jobs (optional).
    If you don't persist to a DB, you can ignore this model.
    """

    __tablename__ = "jobs"

    # Identifiers & inputs
    request_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    max_models: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    trace_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Status & timing
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JobStatus.PENDING.value
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_time_ms: Mapped[Optional[float]] = mapped_column(Float)

    # Results / diagnostics
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def apply_from_job(self, job: "QueryJob") -> None:
        """
        Copy identifying & input fields from a QueryJob into this record.
        Does not change status/timestamps/result.
        """
        self.request_id = job.request_id
        self.prompt = job.prompt
        self.mode = job.mode
        self.max_models = job.max_models
        self.trace_id = job.trace_id or None

    def __repr__(self) -> str:
        return (
            f"JobRecord(request_id={self.request_id!r}, status={self.status!r}, "
            f"mode={self.mode!r}, max_models={self.max_models!r})"
        )


# ---------------------
# In-memory job payload
# ---------------------
@dataclass
class QueryJob:
    """Job for processing query requests asynchronously."""

    request_id: str
    prompt: str
    mode: str = "balanced"
    max_models: int = 3
    trace_id: str = ""

    @classmethod
    def from_record(cls, rec: JobRecord) -> "QueryJob":
        """Construct a QueryJob from a JobRecord (used by worker DB fallback)."""
        return cls(
            request_id=rec.request_id,
            prompt=rec.prompt,
            mode=rec.mode,
            max_models=rec.max_models,
            trace_id=rec.trace_id or "",
        )

    async def process(self) -> Dict[str, Any]:
        """
        Execute the pipeline and return a standardized result dict.

        Returns
        -------
        dict
            {
              "request_id": str,
              "answer": str,
              "confidence": float (0..1),
              "winner_model": str,
              "response_time_ms": int,
              "models_used": list[str],
              "status": "completed" | "failed",
              "error": str (only if failed)
            }
        """
        try:
            route_request = RouteRequest(
                prompt=self.prompt,
                options=RouteOptions(
                    model_selection_mode=self.mode,
                    max_parallel_requests=self.max_models,
                ),
            )

            # Run pipeline (expects a dict-like result)
            result: Dict[str, Any] = await run_pipeline(
                pipeline_id="judge",
                req=route_request,
                trace_id=self.trace_id,
            )

            # Normalize key names defensively
            normalized: Dict[str, Any] = {
                "request_id": self.request_id,
                "answer": result.get("answer", ""),
                "confidence": float(result.get("confidence", 0.0) or 0.0),
                "winner_model": result.get("winner_model", ""),
                "response_time_ms": int(result.get("response_time_ms", 0) or 0),
                "models_used": result.get("models_attempted", []) or [],
                "status": JobStatus.COMPLETED.value,
            }
            return normalized

        except Exception as e:
            logger.exception("QueryJob.process failed: %s", e)
            return {
                "request_id": self.request_id,
                "error": str(e),
                "status": JobStatus.FAILED.value,
            }
