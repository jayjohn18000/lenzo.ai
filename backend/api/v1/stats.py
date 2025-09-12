# backend/api/v1/stats.py - Corrected version with proper indentation and response models
"""Real-time usage statistics from SQLite database"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func, text, create_engine
from pydantic import BaseModel
import logging

from backend.database import (
    get_db,
    QueryRequest as DBQueryRequest,
    ModelResponse as DBModelResponse,
)
from backend.database.models import get_session, init_db

logger = logging.getLogger(__name__)


# Response Models for validation
class TopModel(BaseModel):
    name: str
    usage_percentage: float
    avg_score: float
    avg_response_time: float = 0
    win_rate: float = 0


class DailyUsage(BaseModel):
    date: str
    requests: int
    cost: float


class UsageStatsResponse(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    avg_confidence: float
    top_models: List[TopModel]
    daily_usage: List[DailyUsage]
    data_available: bool
    message: Optional[str] = None
    error: Optional[str] = None


class TodayStatsResponse(BaseModel):
    requests: int
    cost: float
    avg_confidence: float
    date: str


class ModelPerformance(BaseModel):
    model: str
    total_calls: int
    wins: int
    win_rate: float
    avg_confidence: float
    avg_response_time_ms: float
    avg_cost: float
    avg_reliability: float
    avg_hallucination_risk: float


class ModelPerformanceResponse(BaseModel):
    models: List[ModelPerformance]
    period_days: int
    last_updated: str
    error: Optional[str] = None


stats_router = APIRouter(prefix="/api/v1", tags=["Statistics"])


@stats_router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_statistics(days: int = Query(default=7, ge=1, le=365)):
    """Get real usage statistics from database"""

    engine = create_engine("sqlite:///nextagi.db")
    db = get_session(engine)

    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get aggregate statistics
        stats = (
            db.query(
                func.count(DBQueryRequest.id).label("total_requests"),
                func.sum(DBQueryRequest.total_tokens_used).label("total_tokens"),
                func.sum(DBQueryRequest.total_cost).label("total_cost"),
                func.avg(DBQueryRequest.response_time_ms).label("avg_response_time"),
                func.avg(DBQueryRequest.winner_confidence).label("avg_confidence"),
            )
            .filter(DBQueryRequest.created_at >= start_date)
            .first()
        )

        # If no data exists
        if not stats.total_requests:
            return UsageStatsResponse(
                total_requests=0,
                total_tokens=0,
                total_cost=0.0,
                avg_response_time=0.0,
                avg_confidence=0.0,
                top_models=[],
                daily_usage=[],
                data_available=False,
                message="No usage data available yet. Start making queries to see statistics!",
            )

        # Get daily usage breakdown
        daily_usage_query = (
            db.query(
                func.date(DBQueryRequest.created_at).label("date"),
                func.count(DBQueryRequest.id).label("requests"),
                func.sum(DBQueryRequest.total_cost).label("cost"),
            )
            .filter(DBQueryRequest.created_at >= start_date)
            .group_by(func.date(DBQueryRequest.created_at))
            .order_by("date")
        )

        daily_usage = [
            DailyUsage(
                date=row.date.strftime("%Y-%m-%d"),
                requests=row.requests,
                cost=float(row.cost or 0),
            )
            for row in daily_usage_query.all()
        ]

        # Get model performance statistics
        model_stats = (
            db.query(
                DBModelResponse.model_name,
                func.count(DBModelResponse.id).label("usage_count"),
                func.avg(DBModelResponse.confidence_score).label("avg_confidence"),
                func.avg(DBModelResponse.response_time_ms).label("avg_response_time"),
                func.sum(DBModelResponse.is_winner).label("wins"),
            )
            .filter(DBModelResponse.created_at >= start_date)
            .group_by(DBModelResponse.model_name)
            .order_by(func.count(DBModelResponse.id).desc())
            .all()
        )

        # Calculate model usage percentages
        total_model_calls = (
            sum(row.usage_count for row in model_stats) if model_stats else 0
        )

        top_models = []
        for row in model_stats[:4]:  # Top 4 models
            if total_model_calls > 0:
                usage_percentage = (row.usage_count / total_model_calls) * 100
                win_rate = (
                    (row.wins / row.usage_count) * 100 if row.usage_count > 0 else 0
                )

                top_models.append(
                    TopModel(
                        name=row.model_name.split("/")[-1],  # Simplify model name
                        usage_percentage=round(usage_percentage, 1),
                        avg_score=round(float(row.avg_confidence or 0), 3),
                        avg_response_time=round(float(row.avg_response_time or 0), 0),
                        win_rate=round(win_rate, 1),
                    )
                )

        # Add "Others" category if needed
        if len(model_stats) > 4:
            others_count = sum(row.usage_count for row in model_stats[4:])
            if others_count > 0 and total_model_calls > 0:
                others_percentage = (others_count / total_model_calls) * 100
                others_avg_confidence = (
                    sum(row.avg_confidence * row.usage_count for row in model_stats[4:])
                    / others_count
                )

                top_models.append(
                    TopModel(
                        name="Others",
                        usage_percentage=round(others_percentage, 1),
                        avg_score=round(float(others_avg_confidence), 3),
                        avg_response_time=0,
                        win_rate=0,
                    )
                )

        # Ensure confidence values are properly bounded
        avg_confidence = float(stats.avg_confidence or 0)
        if avg_confidence > 1.0:
            logger.warning(f"Average confidence {avg_confidence} exceeds 1.0, capping")
            avg_confidence = 1.0

        return UsageStatsResponse(
            total_requests=stats.total_requests or 0,
            total_tokens=stats.total_tokens or 0,
            total_cost=float(stats.total_cost or 0),
            avg_response_time=round(
                float(stats.avg_response_time or 0) / 1000, 1
            ),  # Convert to seconds
            avg_confidence=round(avg_confidence, 3),
            top_models=top_models,
            daily_usage=daily_usage,
            data_available=True,
        )

    except Exception as e:
        logger.error(f"Error fetching usage stats: {e}")
        return UsageStatsResponse(
            total_requests=0,
            total_tokens=0,
            total_cost=0.0,
            avg_response_time=0.0,
            avg_confidence=0.0,
            top_models=[],
            daily_usage=[],
            data_available=False,
            error="Unable to fetch statistics at this time",
        )
    finally:
        db.close()


@stats_router.get("/usage/today", response_model=TodayStatsResponse)
async def get_today_statistics():
    """Get today's statistics for dashboard"""

    engine = create_engine("sqlite:///nextagi.db")
    db = get_session(engine)

    try:
        today = datetime.utcnow().date()

        # Today's stats
        today_stats = (
            db.query(
                func.count(DBQueryRequest.id).label("requests"),
                func.sum(DBQueryRequest.total_cost).label("cost"),
                func.avg(DBQueryRequest.winner_confidence).label("avg_confidence"),
            )
            .filter(func.date(DBQueryRequest.created_at) == today)
            .first()
        )

        # Ensure confidence is bounded
        avg_confidence = float(today_stats.avg_confidence or 0)
        avg_confidence = min(1.0, max(0.0, avg_confidence))

        return TodayStatsResponse(
            requests=today_stats.requests or 0,
            cost=float(today_stats.cost or 0),
            avg_confidence=round(avg_confidence, 3),
            date=today.strftime("%Y-%m-%d"),
        )

    except Exception as e:
        logger.error(f"Error fetching today's stats: {e}")
        return TodayStatsResponse(
            requests=0,
            cost=0.0,
            avg_confidence=0.0,
            date=datetime.utcnow().date().strftime("%Y-%m-%d"),
        )
    finally:
        db.close()


@stats_router.get("/models/performance", response_model=ModelPerformanceResponse)
async def get_model_performance(days: int = Query(default=7, ge=1, le=365)):
    """Get detailed model performance metrics"""

    engine = create_engine("sqlite:///nextagi.db")
    db = get_session(engine)

    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get detailed model metrics
        model_metrics = (
            db.query(
                DBModelResponse.model_name,
                func.count(DBModelResponse.id).label("total_calls"),
                func.sum(DBModelResponse.is_winner).label("wins"),
                func.avg(DBModelResponse.confidence_score).label("avg_confidence"),
                func.avg(DBModelResponse.response_time_ms).label("avg_response_time"),
                func.avg(DBModelResponse.cost).label("avg_cost"),
                func.avg(DBModelResponse.reliability_score).label("avg_reliability"),
                func.avg(DBModelResponse.hallucination_risk).label(
                    "avg_hallucination_risk"
                ),
            )
            .filter(DBModelResponse.created_at >= start_date)
            .group_by(DBModelResponse.model_name)
            .all()
        )

        performance_data = []
        for row in model_metrics:
            # Ensure all confidence/score values are bounded
            confidence = min(1.0, max(0.0, float(row.avg_confidence or 0)))
            reliability = min(1.0, max(0.0, float(row.avg_reliability or 0)))
            hallucination_risk = min(
                1.0, max(0.0, float(row.avg_hallucination_risk or 0))
            )

            performance_data.append(
                ModelPerformance(
                    model=row.model_name,
                    total_calls=row.total_calls,
                    wins=row.wins or 0,
                    win_rate=round(
                        (
                            (row.wins / row.total_calls * 100)
                            if row.total_calls > 0
                            else 0
                        ),
                        1,
                    ),
                    avg_confidence=round(confidence, 3),
                    avg_response_time_ms=round(float(row.avg_response_time or 0), 0),
                    avg_cost=round(float(row.avg_cost or 0), 4),
                    avg_reliability=round(reliability, 3),
                    avg_hallucination_risk=round(hallucination_risk, 3),
                )
            )

        # Sort by win rate
        performance_data.sort(key=lambda x: x.win_rate, reverse=True)

        return ModelPerformanceResponse(
            models=performance_data,
            period_days=days,
            last_updated=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error fetching model performance: {e}")
        return ModelPerformanceResponse(
            models=[],
            period_days=days,
            last_updated=datetime.utcnow().isoformat(),
            error=str(e),
        )
    finally:
        db.close()
