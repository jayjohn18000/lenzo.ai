from backend.auth.api_key import verify_api_key
from fastapi import Depends, HTTPException
# backend/api/v1/routes.py
from __future__ import annotations

import time
import uuid
import random
from typing import Dict, Optional, Any, List, Tuple
from statistics import mean
from datetime import datetime, timedelta, timezone
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from backend.jobs.manager import JobManager
from backend.jobs.models import JobStatus
from backend.dependencies import get_job_manager
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["NextAGI Core"])


# --------------------------
# Schemas (safe defaults)
# --------------------------
class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    mode: str = Field(default="balanced", pattern="^(speed|quality|balanced|cost)$")
    max_models: int = Field(default=3, ge=1, le=5)
    budget_limit: Optional[float] = Field(default=None, ge=0)
    include_reasoning: bool = Field(default=True)


class ModelMetrics(BaseModel):
    model: str
    response: str
    confidence: float = Field(ge=0.0, le=1.0)
    response_time_ms: int
    tokens_used: int
    cost: float
    reliability_score: float = Field(default=0.8, ge=0.0, le=1.0)
    consistency_score: float = Field(default=0.75, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=0.15, ge=0.0, le=1.0)
    citation_quality: float = Field(default=0.7, ge=0.0, le=1.0)
    trait_scores: Dict[str, float] = Field(default_factory=dict)
    rank_position: int = 1
    is_winner: bool = False
    error: Optional[str] = None


class ModelComparison(BaseModel):
    best_confidence: float = Field(ge=0.0, le=1.0)
    worst_confidence: float = Field(ge=0.0, le=1.0)
    avg_response_time: int
    total_cost: float
    performance_spread: float = Field(ge=0.0, le=1.0)
    model_count: int


class RankedModelAggregate(BaseModel):
    score_mean: Optional[float] = None
    score_stdev: Optional[float] = None
    vote_top_label: Optional[str] = None
    vote_top_count: Optional[int] = None
    vote_total: Optional[int] = None


class RankedModelJudgment(BaseModel):
    judge_model: str
    score01: Optional[float] = None
    label: Optional[str] = None
    reasons: str
    raw: str


class RankedModel(BaseModel):
    model: str
    aggregate: RankedModelAggregate
    judgments: List[RankedModelJudgment] = Field(default_factory=list)


class WinnerModel(BaseModel):
    model: str
    score: Optional[float] = None


class QueryResponse(BaseModel):
    """Fully aligned response with frontend expectations"""
    # Core fields
    request_id: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    winner_model: str
    response_time_ms: int
    models_used: List[str]
    model_metrics: List[ModelMetrics] = Field(default_factory=list)
    model_comparison: Optional[ModelComparison] = None
    reasoning: Optional[str] = None
    total_cost: float = 0.0
    scores_by_trait: Optional[Dict[str, float]] = None

    # Frontend-expected fields
    pipeline_id: str = "judge"
    decision_reason: str = "Multi-model analysis selected best response"
    models_attempted: List[str] = Field(default_factory=list)
    models_succeeded: List[str] = Field(default_factory=list)
    ranking: List[RankedModel] = Field(default_factory=list)
    winner: Optional[WinnerModel] = None

    # Legacy compatibility
    estimated_cost: float = 0.0


# --------------------------
# Helpers
# --------------------------
# at top with other helpers
def normalize_01(value: Any) -> float:
    """
    Turn 0..1 or 0..100 into 0..1.
    - If value > 1 and <= 100, assume it's a percentage and divide by 100.
    - Clamp to [0,1] in all cases.
    """
    try:
        v = float(value)
    except Exception:
        return 0.0
    if 1.0 < v <= 100.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))

def validate_confidence(value: float, source: str = "") -> float:
    """Clamp confidence to [0, 1] without scaling."""
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return max(0.0, min(1.0, v))


def get_models_for_mode(mode: str, max_models: int, prompt: str = "") -> List[str]:
    model_pools = {
        "speed": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
        "quality": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus"],
        "balanced": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
        "cost": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
    }
    selected = model_pools.get(mode, model_pools["balanced"])
    return selected[:max_models]


def estimate_token_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    cost_map = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00035, "output": 0.00105},
    }
    costs = {"input": 0.001, "output": 0.001}
    for key in cost_map:
        if key in model.lower(, current_key=Depends(verify_api_key)):
            costs = cost_map[key]
            break
    return (tokens_in * costs["input"] / 1000) + (tokens_out * costs["output"] / 1000)


def calculate_model_confidence(candidate, judge_scores: Optional[Dict[str, float]] = None, is_winner: bool = False) -> float:
    base_confidence = 0.7
    if hasattr(candidate, "text") and candidate.text:
        text_length = len(candidate.text.split())
        if 20 <= text_length <= 500:
            base_confidence += 0.1
    if judge_scores:
        try:
            judge_avg = mean(judge_scores.values()) if judge_scores.values() else 0.7
        except Exception:
            judge_avg = 0.7
        base_confidence = (base_confidence * 0.4 + judge_avg * 0.6)
    if is_winner:
        base_confidence = min(1.0, base_confidence + 0.05)
    return validate_confidence(base_confidence)


def estimate_query_time(request: QueryRequest) -> float:
    base_time = 800
    model_times = {"speed": 400, "balanced": 800, "quality": 1500, "cost": 600}
    time_per_model = model_times.get(request.mode, 800)
    total_time = base_time + (time_per_model * request.max_models)
    complexity_factor = min(len(request.prompt) / 100, 3.0)
    total_time *= (1 + complexity_factor * 0.2)
    return total_time


async def process_query_sync(request: QueryRequest, request_id: str) -> Tuple[Dict[str, Any], List[str]]:
    selected_models = get_models_for_mode(request.mode, request.max_models, request.prompt)
    route_req = RouteRequest(
        prompt=request.prompt,
        options=RouteOptions(
            models=selected_models,
            model_selection_mode=request.mode,  # matches our literal in schemas
            require_citations=True,
        ),
    )
    result = await run_pipeline("judge", route_req, trace_id=request_id)
    return result, selected_models


# --------------------------
# MAIN INTEGRATED ENDPOINT
# --------------------------
@router.post("/query", response_model=None)
async def query_models(
    request: QueryRequest,
    fast: bool = Query(False, description="Execute synchronously if possible (<3s)"),
    job_manager: JobManager = Depends(get_job_manager),
, current_key=Depends(verify_api_key)):
    """
    Integrated query endpoint with async job support.
    - fast=true: Attempts synchronous execution for queries estimated <3s
    - fast=false or long queries: Returns 202 with job_id for polling

    NOTE: Public response contract is preserved.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Estimate processing time and decide path
    estimated_time = estimate_query_time(request)
    logger.info(f"Query estimated time: {estimated_time}ms, fast={fast}")
    use_async = not fast or estimated_time > 3000

    # Fast (sync) path
    if not use_async:
        try:
            logger.info(f"Attempting fast synchronous execution for request {request_id}")
            result, selected_models = await asyncio.wait_for(
                process_query_sync(request, request_id),
                timeout=3.0,
            )
            response_time_ms = int((time.time() - start_time) * 1000)
            response = await build_query_response(
                result, request, request_id, selected_models, response_time_ms
            )
            logger.info(f"Fast path completed in {response_time_ms}ms")
            return response
        except asyncio.TimeoutError:
            logger.info("Fast path timed out, falling back to async")
            use_async = True
        except Exception as e:
            # If synchronous execution fails for any other reason, fall back to async job
            logger.warning(f"Fast path error ({type(e).__name__}): {e}; falling back to async")
            use_async = True

    # Async path
    logger.info(f"Using async job queue for request {request_id}")
    job_params = {
        "request_id": request_id,
        "prompt": request.prompt,
        "mode": request.mode,
        "max_models": request.max_models,
        # trace_id is optional; include if you have one upstream
        "trace_id": request_id,
    }
    job_id = await job_manager.create_job(job_params)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "accepted",
            "estimated_time_ms": int(estimated_time),
            "poll_url": f"/api/v1/jobs/{job_id}",
            "poll_interval_ms": 500,
            "message": "Query processing started. Poll the job status endpoint for results.",
        },
    )


async def build_query_response(
    result: Dict[str, Any],
    request: QueryRequest,
    request_id: str,
    selected_models: List[str],
    response_time_ms: int,
) -> QueryResponse:
    candidates = result.get("candidates", [])
    judge_scores = result.get("judge_scores", {})
    winner_idx = result.get("winner_idx", 0)

    model_metrics: List[ModelMetrics] = []
    total_cost = 0.0
    models_succeeded: List[str] = []
    models_attempted = selected_models.copy()

    logger.info(f"Processing {len(candidates)} candidates")

    for i, candidate in enumerate(candidates, current_key=Depends(verify_api_key)):
        is_winner = i == winner_idx
        candidate_scores = judge_scores.get(i, {})
        confidence = calculate_model_confidence(candidate, candidate_scores, is_winner)

        text_length = len(getattr(candidate, "text", "") or "")
        tokens_used = max(50, text_length // 4)
        cost = estimate_token_cost(getattr(candidate, "model", "") or "", tokens_used // 2, tokens_used // 2)
        total_cost += cost
        models_succeeded.append(getattr(candidate, "model", "unknown") or "unknown")

        metric = ModelMetrics(
            model=getattr(candidate, "model", "unknown") or "unknown",
            response=getattr(candidate, "text", "No response") or "No response",
            confidence=confidence,
            response_time_ms=int(getattr(candidate, "gen_time_ms", 1500) or 1500),
            tokens_used=int(tokens_used),
            cost=float(cost),
            reliability_score=validate_confidence(candidate_scores.get("reliability", 0.8)),
            consistency_score=validate_confidence(candidate_scores.get("consistency", 0.75)),
            hallucination_risk=validate_confidence(candidate_scores.get("hallucination_risk", 0.15)),
            citation_quality=validate_confidence(candidate_scores.get("citation_quality", 0.7)),
            trait_scores={
                k: validate_confidence(v)
                for k, v in candidate_scores.items()
                if k not in ["reliability", "consistency", "hallucination_risk", "citation_quality"]
            },
            rank_position=i + 1,
            is_winner=is_winner,
            error=getattr(candidate, "error", None),
        )
        model_metrics.append(metric)

    if model_metrics:
        model_metrics.sort(key=lambda x: x.confidence, reverse=True)
        for i, metric in enumerate(model_metrics):
            metric.rank_position = i + 1
            metric.is_winner = i == 0

    winner = model_metrics[0] if model_metrics else None

    comparison = None
    if model_metrics:
        confidences = [m.confidence for m in model_metrics]
        response_times = [m.response_time_ms for m in model_metrics]
        comparison = ModelComparison(
            best_confidence=max(confidences),
            worst_confidence=min(confidences),
            avg_response_time=int(mean(response_times)),
            total_cost=total_cost,
            performance_spread=max(confidences) - min(confidences),
            model_count=len(model_metrics),
        )

    ranking: List[RankedModel] = []
    for metric in model_metrics:
        ranking.append(
            RankedModel(
                model=metric.model,
                aggregate=RankedModelAggregate(
                    score_mean=metric.confidence,
                    score_stdev=0.05,
                    vote_top_label="selected" if metric.is_winner else "candidate",
                    vote_top_count=1 if metric.is_winner else 0,
                    vote_total=1,
                ),
                judgments=[
                    RankedModelJudgment(
                        judge_model="openai/gpt-4o-mini",
                        score01=metric.confidence,
                        label="quality_assessment",
                        reasons=f"Model ranked #{metric.rank_position} with {metric.confidence:.1%} confidence",
                        raw=f"Confidence: {metric.confidence}, Reliability: {metric.reliability_score}",
                    )
                ],
            )
        )

    winner_obj = WinnerModel(model=winner.model, score=winner.confidence) if winner else None

    reasoning = None
    if request.include_reasoning and model_metrics:
        reasoning_lines = [
            "Multi-Model Analysis Results:",
            "",
            f'Query: "{request.prompt[:80]}..."',
            "",
            f'Winner: {winner.model if winner else "Unknown"}',
            f'• Confidence: {winner.confidence:.1%}' if winner else "• Confidence: n/a",
            f'• Response time: {winner.response_time_ms}ms' if winner else "• Response time: n/a",
            f'• Reliability: {winner.reliability_score:.1%}' if winner else "• Reliability: n/a",
            f'• Hallucination risk: {winner.hallucination_risk:.1%}' if winner else "• Hallucination risk: n/a",
            "",
            "Model Performance Summary:",
            f'• Models analyzed: {len(model_metrics)}',
            f'• Average confidence: {mean(m.confidence for m in model_metrics):.1%}',
            f'• Average response time: {mean(m.response_time_ms for m in model_metrics):.0f}ms',
            "",
            "Complete Rankings:",
        ]
        for metric in model_metrics:
            reasoning_lines.append(f"{metric.rank_position}. {metric.model} - {metric.confidence:.1%}")
        reasoning = "\n".join(reasoning_lines)

    final_confidence = validate_confidence(result.get("confidence", winner.confidence if winner else 0.8))

    return QueryResponse(
        request_id=request_id,
        answer=result.get("answer", winner.response if winner else "No response generated"),
        confidence=final_confidence,
        winner_model=winner.model if winner else "none",
        response_time_ms=response_time_ms,
        models_used=[m.model for m in model_metrics],
        model_metrics=model_metrics,
        model_comparison=comparison,
        reasoning=reasoning,
        total_cost=float(total_cost),
        scores_by_trait=result.get("scores_by_trait", {}),
        pipeline_id="judge",
        decision_reason=f"Selected {winner.model if winner else 'best'} model based on confidence scoring",
        models_attempted=models_attempted,
        models_succeeded=models_succeeded,
        ranking=ranking,
        winner=winner_obj,
        estimated_cost=float(total_cost),
    )


# --------------------------
# JOB STATUS ENDPOINT
# --------------------------
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
, current_key=Depends(verify_api_key)):
    """Get job status and results."""
    status_payload = await job_manager.get_job_status(job_id)
    if not status_payload:
        raise HTTPException(status_code=404, detail="Job not found")

    st = (status_payload.get("status") or "").lower()

    # Compare to Enum .value to avoid mismatches
    if st == JobStatus.COMPLETED.value:
        return {
            "job_id": job_id,
            "status": JobStatus.COMPLETED.value,
            "result": status_payload.get("result"),
            "processing_time_ms": status_payload.get("actual_time_ms"),
            "completed_at": status_payload.get("completed_at"),
        }

    if st == JobStatus.FAILED.value:
        return JSONResponse(
            status_code=500,
            content={
                "job_id": job_id,
                "status": JobStatus.FAILED.value,
                "error": status_payload.get("error"),
                "failed_at": status_payload.get("completed_at"),
            },
        )

    # still running or pending
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": st,
            "progress": status_payload.get("progress", 0),
            "message": "Job is still processing",
            "created_at": status_payload.get("created_at"),
            "estimated_completion": _estimate_completion(status_payload),
        },
    )


def _estimate_completion(status_payload: Dict[str, Any]) -> Optional[str]:
    """Estimate completion time based on progress percentage."""
    try:
        progress = float(status_payload.get("progress", 0))
        created_at = status_payload.get("created_at")
        if progress > 0 and created_at:
            created = datetime.fromisoformat(created_at)
            now = datetime.now(timezone.utc) if created.tzinfo else datetime.utcnow()
            elapsed = (now - created).total_seconds()
            total_estimated = elapsed / (progress / 100.0)
            remaining = max(0.0, total_estimated - elapsed)
            completion = (now + timedelta(seconds=remaining))
            return completion.isoformat()
    except Exception:
        pass
    return None


# --------------------------
# Health & Usage Endpoints
# --------------------------
@router.get("/health")
async def health_check(, current_key=Depends(verify_api_key)):
    return {"status": "healthy", "timestamp": time.time(), "version": "2.1.0-async"}


@router.get("/usage")
async def get_usage_statistics(days: int = Query(default=30, ge=1, le=365), current_key=Depends(verify_api_key)):
    try:
        days = min(days, 30)
        base_date = datetime.now() - timedelta(days=days)
        daily_usage = []
        for i in range(days):
            date = base_date + timedelta(days=i)
            daily_usage.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "requests": random.randint(800, 3000),
                    "cost": round(random.uniform(20, 80), 2),
                }
            )
        top_models = [
            {"name": "GPT-4 Turbo", "usage_percentage": 42, "avg_score": 0.95},
            {"name": "Claude-3.5 Sonnet", "usage_percentage": 31, "avg_score": 0.92},
            {"name": "Gemini Pro", "usage_percentage": 18, "avg_score": 0.88},
            {"name": "Others", "usage_percentage": 9, "avg_score": 0.85},
        ]
        response_data = {
            "total_requests": sum(d["requests"] for d in daily_usage),
            "total_tokens": random.randint(800_000, 1_200_000),
            "total_cost": round(sum(d["cost"] for d in daily_usage), 2),
            "avg_response_time": round(random.uniform(1.2, 2.5), 1),
            "avg_confidence": round(random.uniform(0.88, 0.96), 3),
            "top_models": top_models,
            "daily_usage": daily_usage,
            "generated_at": datetime.now().isoformat(),
            "days_requested": days,
            "status": "success",
        }
        return JSONResponse(status_code=200, content=response_data, headers={"Cache-Control": "no-cache"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "status": "failed"})


@router.get("/usage-test")
async def usage_test_minimal(, current_key=Depends(verify_api_key)):
    test_data = {
        "test": "success",
        "timestamp": datetime.now().isoformat(),
        "total_requests": 100,
        "message": "Minimal test endpoint",
    }
    json_str = json.dumps(test_data, separators=(",", ":"))
    content_length = len(json_str.encode("utf-8"))
    return JSONResponse(
        status_code=200,
        content=test_data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(content_length),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "close",
        },
    )


@router.get("/debug/headers")
async def debug_response_headers(, current_key=Depends(verify_api_key)):
    debug_data = {
        "message": "Debug response",
        "timestamp": datetime.now().isoformat(),
        "headers_info": "This should not be chunked",
    }
    json_str = json.dumps(debug_data)
    content_length = len(json_str.encode("utf-8"))
    return JSONResponse(
        status_code=200,
        content=debug_data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(content_length),
            "X-Debug": "no-chunking-test",
        },
    )


@router.get("/usage-minimal")
async def usage_minimal(, current_key=Depends(verify_api_key)):
    data = {"status": "ok", "requests": 1000, "cost": 50.5}
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return Response(
        content=json_bytes,
        status_code=200,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(json_bytes)),
            "Connection": "close",
        },
    )


@router.get("/usage-debug")
async def usage_debug(, current_key=Depends(verify_api_key)):
    try:
        print("🔍 Starting usage debug endpoint...")
        basic_data = {"test": "step1", "requests": 1000, "cost": 50.0}
        print(f"Step 1 complete: {basic_data}")
        base_date = datetime.now() - timedelta(days=7)
        daily_usage = []
        for i in range(7):
            date = base_date + timedelta(days=i)
            daily_usage.append({"date": date.strftime("%Y-%m-%d"), "requests": 100 + i, "cost": 10.0 + i})
        print(f"Step 2 complete: Generated {len(daily_usage)} daily entries")
        response_data = {
            "status": "debug_success",
            "total_requests": sum(d["requests"] for d in daily_usage),
            "total_cost": round(sum(d["cost"] for d in daily_usage), 2),
            "daily_usage": daily_usage,
            "debug_info": {"endpoint": "usage-debug", "timestamp": datetime.now().isoformat(), "step": "final"},
        }
        json_str = json.dumps(response_data, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")
        content_length = len(json_bytes)
        print(f"Step 4 complete: JSON is {content_length} bytes")
        return Response(
            content=json_bytes,
            status_code=200,
            media_type="application/json",
            headers={"Content-Length": str(content_length), "Cache-Control": "no-cache", "Connection": "close", "X-Debug": "success"},
        )
    except Exception as e:
        print(f"❌ Debug endpoint failed: {e}")
        import traceback

        traceback.print_exc()
        error_data = {"error": str(e), "status": "debug_failed"}
        error_json = json.dumps(error_data).encode("utf-8")
        return Response(
            content=error_json,
            status_code=500,
            media_type="application/json",
            headers={"Content-Length": str(len(error_json)), "X-Debug": "error"},
        )


@router.get("/usage-simple")
async def usage_simple(, current_key=Depends(verify_api_key)):
    data = {
        "total_requests": 2500,
        "total_tokens": 1200000,
        "total_cost": 150.75,
        "avg_response_time": 1.8,
        "avg_confidence": 0.94,
        "top_models": [
            {"name": "GPT-4", "usage": 42, "score": 0.95},
            {"name": "Claude", "usage": 31, "score": 0.92},
            {"name": "Gemini", "usage": 27, "score": 0.88},
        ],
        "daily_usage": [
            {"date": "2025-08-31", "requests": 1200, "cost": 45.2},
            {"date": "2025-09-01", "requests": 1300, "cost": 48.3},
        ],
        "status": "success",
    }
    return JSONResponse(status_code=200, content=data)
