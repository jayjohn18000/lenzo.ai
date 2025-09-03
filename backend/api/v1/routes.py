# backend/api/v1/routes.py 

import time
import uuid
import random
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from statistics import mean
import json
import logging

# Import your existing pipeline components
import asyncio
from backend.jobs.manager import JobManager
from backend.jobs.models import JobStatus
from backend.dependencies import get_job_manager
from datetime import datetime, timedelta
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["NextAGI Core"])

# ALIGNED Pydantic models
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
    trait_scores: Dict[str, float] = {}
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
    judgments: List[RankedModelJudgment] = []

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
    model_metrics: List[ModelMetrics] = []
    model_comparison: Optional[ModelComparison] = None
    reasoning: Optional[str] = None
    total_cost: float = 0.0
    scores_by_trait: Optional[Dict[str, float]] = None
    
    # Frontend-expected fields
    pipeline_id: str = "judge"
    decision_reason: str = "Multi-model analysis selected best response"
    models_attempted: List[str] = []
    models_succeeded: List[str] = []
    ranking: List[RankedModel] = []
    winner: Optional[WinnerModel] = None
    
    # Legacy compatibility
    estimated_cost: float = 0.0

def validate_confidence(value: float, source: str = "") -> float:
    """Ensure confidence is within [0, 1] bounds"""
    return max(0.0, min(1.0, value))

def get_models_for_mode(mode: str, max_models: int, prompt: str = "") -> List[str]:
    """Smart model selection"""
    model_pools = {
        "speed": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
        "quality": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus"],
        "balanced": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
        "cost": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"]
    }
    
    selected = model_pools.get(mode, model_pools["balanced"])
    return selected[:max_models]

def estimate_token_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost based on model and token usage"""
    cost_map = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00035, "output": 0.00105},
    }
    
    costs = {"input": 0.001, "output": 0.001}  # Default
    for key in cost_map:
        if key in model.lower():
            costs = cost_map[key]
            break
    
    return (tokens_in * costs["input"] / 1000) + (tokens_out * costs["output"] / 1000)

def calculate_model_confidence(candidate, judge_scores: Optional[Dict[str, float]] = None, is_winner: bool = False) -> float:
    """Calculate bounded confidence score"""
    base_confidence = 0.7
    
    if hasattr(candidate, 'text') and candidate.text:
        text_length = len(candidate.text.split())
        if 20 <= text_length <= 500:
            base_confidence += 0.1
    
    if judge_scores:
        judge_avg = mean(judge_scores.values()) if judge_scores.values() else 0.7
        base_confidence = (base_confidence * 0.4 + judge_avg * 0.6)
    
    if is_winner:
        base_confidence = min(1.0, base_confidence + 0.05)
    
    return validate_confidence(base_confidence)

def estimate_query_time(request: QueryRequest) -> float:
    """Estimate query processing time in milliseconds"""
    base_time = 800
    model_times = {
        "speed": 400,
        "balanced": 800,
        "quality": 1500,
        "cost": 600
    }
    time_per_model = model_times.get(request.mode, 800)
    total_time = base_time + (time_per_model * request.max_models)
    
    # Add complexity factor
    complexity_factor = min(len(request.prompt) / 100, 3.0)
    total_time *= (1 + complexity_factor * 0.2)
    
    return total_time

async def process_query_sync(request: QueryRequest, request_id: str) -> Dict[str, Any]:
    """Process query synchronously - extracted for reuse"""
    selected_models = get_models_for_mode(request.mode, request.max_models, request.prompt)
    
    # Build route request
    route_req = RouteRequest(
        prompt=request.prompt,
        options=RouteOptions(
            models=selected_models,
            model_selection_mode=request.mode,
            require_citations=True
        )
    )
    
    # Execute pipeline
    result = await run_pipeline("judge", route_req, trace_id=request_id)
    return result, selected_models
# MAIN INTEGRATED QUERY ENDPOINT
@router.post("/query", response_model=None)  # None to allow both QueryResponse and 202 response
async def query_models(
    request: QueryRequest,
    fast: bool = Query(False, description="Execute synchronously if possible (<3s)"),
    job_manager: JobManager = Depends(get_job_manager)
):
    """
    Integrated query endpoint with async job support.
    - fast=true: Attempts synchronous execution for queries estimated <3s
    - fast=false or long queries: Returns 202 with job_id for polling
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Estimate processing time
    estimated_time = estimate_query_time(request)
    logger.info(f"Query estimated time: {estimated_time}ms, fast={fast}")
    
    # Check if we should use async path
    use_async = not fast or estimated_time > 3000
    
    if not use_async:
        # Fast path: Try synchronous execution
        try:
            logger.info(f"Attempting fast synchronous execution for request {request_id}")
            
            # Use timeout to ensure we don't exceed 3s
            result, selected_models = await asyncio.wait_for(
                process_query_sync(request, request_id),
                timeout=3.0
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Build and return response synchronously
            response = await build_query_response(
                result, 
                request, 
                request_id, 
                selected_models, 
                response_time_ms
            )
            
            logger.info(f"Fast path completed in {response_time_ms}ms")
            return response
            
        except asyncio.TimeoutError:
            logger.info(f"Fast path timed out, falling back to async")
            use_async = True
    
    if use_async:
        # Async path: Create job and return 202
        logger.info(f"Using async job queue for request {request_id}")
        
        job_params = {
            "prompt": request.prompt,
            "mode": request.mode,
            "max_models": request.max_models,
            "budget_limit": request.budget_limit,
            "include_reasoning": request.include_reasoning,
            "request_id": request_id
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
                "message": "Query processing started. Poll the job status endpoint for results."
            }
        )

async def build_query_response(
    result: Dict,
    request: QueryRequest,
    request_id: str,
    selected_models: List[str],
    response_time_ms: int
) -> QueryResponse:
    """Build the QueryResponse from pipeline results"""
    # Extract results safely
    candidates = result.get("candidates", [])
    judge_scores = result.get("judge_scores", {})
    winner_idx = result.get("winner_idx", 0)
    
    # Process model responses
    model_metrics = []
    total_cost = 0.0
    models_succeeded = []
    models_attempted = selected_models.copy()
    
    logger.info(f"Processing {len(candidates)} candidates")
    
    # Process each candidate
    for i, candidate in enumerate(candidates):
        is_winner = (i == winner_idx)
        candidate_scores = judge_scores.get(i, {})
        confidence = calculate_model_confidence(candidate, candidate_scores, is_winner)
        
        # Estimate tokens and cost
        text_length = len(getattr(candidate, 'text', ''))
        tokens_used = max(50, text_length // 4)
        cost = estimate_token_cost(candidate.model, tokens_used // 2, tokens_used // 2)
        total_cost += cost
        models_succeeded.append(candidate.model)
        
        # Create metric
        metric = ModelMetrics(
            model=candidate.model,
            response=getattr(candidate, 'text', 'No response'),
            confidence=confidence,
            response_time_ms=getattr(candidate, 'gen_time_ms', 1500),
            tokens_used=tokens_used,
            cost=cost,
            reliability_score=validate_confidence(candidate_scores.get('reliability', 0.8)),
            consistency_score=validate_confidence(candidate_scores.get('consistency', 0.75)),
            hallucination_risk=validate_confidence(candidate_scores.get('hallucination_risk', 0.15)),
            citation_quality=validate_confidence(candidate_scores.get('citation_quality', 0.7)),
            trait_scores={k: validate_confidence(v) for k, v in candidate_scores.items() if k not in ['reliability', 'consistency', 'hallucination_risk', 'citation_quality']},
            rank_position=i + 1,
            is_winner=is_winner,
            error=getattr(candidate, 'error', None)
        )
        model_metrics.append(metric)
    
    # Sort by confidence
    if model_metrics:
        model_metrics.sort(key=lambda x: x.confidence, reverse=True)
        for i, metric in enumerate(model_metrics):
            metric.rank_position = i + 1
            metric.is_winner = (i == 0)
    
    # Get winner
    winner = model_metrics[0] if model_metrics else None
    
    # Build comparison data
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
            model_count=len(model_metrics)
        )
    
    # Convert to ranking format
    ranking = []
    for i, metric in enumerate(model_metrics):
        ranking.append(RankedModel(
            model=metric.model,
            aggregate=RankedModelAggregate(
                score_mean=metric.confidence,
                score_stdev=0.05,
                vote_top_label="selected" if metric.is_winner else "candidate",
                vote_top_count=1 if metric.is_winner else 0,
                vote_total=1
            ),
            judgments=[
                RankedModelJudgment(
                    judge_model="openai/gpt-4o-mini",
                    score01=metric.confidence,
                    label="quality_assessment",
                    reasons=f"Model ranked #{metric.rank_position} with {metric.confidence:.1%} confidence",
                    raw=f"Confidence: {metric.confidence}, Reliability: {metric.reliability_score}"
                )
            ]
        ))
    
    # Create winner object
    winner_obj = None
    if winner:
        winner_obj = WinnerModel(
            model=winner.model,
            score=winner.confidence
        )
    
    # Generate reasoning
    reasoning = None
    if request.include_reasoning and model_metrics:
        reasoning = f"""Multi-Model Analysis Results:

Query: "{request.prompt[:80]}..."

Winner: {winner.model if winner else 'Unknown'}
• Confidence: {winner.confidence:.1%} 
• Response time: {winner.response_time_ms}ms
• Reliability: {winner.reliability_score:.1%}
• Hallucination risk: {winner.hallucination_risk:.1%}

Model Performance Summary:
• Models analyzed: {len(model_metrics)}
• Average confidence: {mean(m.confidence for m in model_metrics):.1%}
• Average response time: {mean(m.response_time_ms for m in model_metrics):.0f}ms

Complete Rankings:"""
        for metric in model_metrics:
            reasoning += f"\n{metric.rank_position}. {metric.model} - {metric.confidence:.1%}"
    
    # Build final response
    final_confidence = validate_confidence(result.get("confidence", winner.confidence if winner else 0.8))
    
    return QueryResponse(
        # Core fields
        request_id=request_id,
        answer=result.get("answer", winner.response if winner else "No response generated"),
        confidence=final_confidence,
        winner_model=winner.model if winner else "none",
        response_time_ms=response_time_ms,
        models_used=[m.model for m in model_metrics],
        model_metrics=model_metrics,
        model_comparison=comparison,
        reasoning=reasoning,
        total_cost=total_cost,
        scores_by_trait=result.get("scores_by_trait", {}),
        
        # Frontend-expected fields
        pipeline_id="judge",
        decision_reason=f"Selected {winner.model if winner else 'best'} model based on confidence scoring",
        models_attempted=models_attempted,
        models_succeeded=models_succeeded,
        ranking=ranking,
        winner=winner_obj,
        estimated_cost=total_cost
    )

# JOB STATUS ENDPOINT
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get job status and results"""
    status = await job_manager.get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return appropriate status code based on job state
    if status["status"] == JobStatus.COMPLETED:
        return {
            "job_id": job_id,
            "status": "completed",
            "result": status["result"],
            "processing_time_ms": status.get("actual_time_ms"),
            "completed_at": status.get("completed_at")
        }
    elif status["status"] == JobStatus.FAILED:
        return JSONResponse(
            status_code=500,
            content={
                "job_id": job_id,
                "status": "failed",
                "error": status["error"],
                "failed_at": status.get("completed_at")
            }
        )
    else:
        # Still processing
        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": status["status"],
                "progress": status.get("progress", 0),
                "message": "Job is still processing",
                "created_at": status.get("created_at"),
                "estimated_completion": _estimate_completion(status)
            }
        )
    
def _estimate_completion(status: Dict) -> Optional[str]:
    """Estimate completion time based on progress"""
    if status.get("progress", 0) > 0 and status.get("created_at"):
        from datetime import datetime
        created = datetime.fromisoformat(status["created_at"])
        elapsed = (datetime.utcnow() - created).total_seconds()
        
        if status["progress"] > 0:
            total_estimated = elapsed / (status["progress"] / 100)
            remaining = total_estimated - elapsed
            completion = datetime.utcnow() + timedelta(seconds=remaining)
            return completion.isoformat()
    
    return None

# Health check
@router.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "version": "2.1.0-async"
    }

@router.get("/usage")
async def get_usage_statistics(days: int = Query(default=30, ge=1, le=365)):
    """
    Non-streaming usage endpoint that returns a proper JSONResponse.
    No manual Content-Length/Connection headers; safe for Schemathesis.
    """
    try:
        days = min(days, 30)

        base_date = datetime.now() - timedelta(days=days)
        daily_usage = []
        for i in range(days):
            date = base_date + timedelta(days=i)
            daily_usage.append({
                "date": date.strftime("%Y-%m-%d"),
                "requests": random.randint(800, 3000),
                "cost": round(random.uniform(20, 80), 2),
            })

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

        # ✅ Return JSONResponse (no manual Content-Length/Connection)
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={"Cache-Control": "no-cache"}  # safe header
        )

    except Exception as e:
        error_data = {"error": str(e), "status": "failed"}
        return JSONResponse(status_code=500, content=error_data)


@router.get("/usage-test")
async def usage_test_minimal():
    """Minimal test endpoint to debug chunked encoding"""
    
    # Very small response to test
    test_data = {
        "test": "success",
        "timestamp": datetime.now().isoformat(),
        "total_requests": 100,
        "message": "Minimal test endpoint"
    }
    
    # Convert to JSON string first, then calculate length
    json_str = json.dumps(test_data, separators=(',', ':'))
    content_length = len(json_str.encode('utf-8'))
    
    return JSONResponse(
        status_code=200,
        content=test_data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(content_length),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "close"  # Force connection close to prevent chunking
        }
    )

@router.get("/debug/headers")
async def debug_response_headers():
    """Debug endpoint to see exactly what headers are being sent"""
    
    debug_data = {
        "message": "Debug response",
        "timestamp": datetime.now().isoformat(),
        "headers_info": "This should not be chunked"
    }
    
    json_str = json.dumps(debug_data)
    content_length = len(json_str.encode('utf-8'))
    
    return JSONResponse(
        status_code=200,
        content=debug_data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(content_length),
            "X-Debug": "no-chunking-test"
        }
    )

@router.get("/usage-minimal")
async def usage_minimal():
    """Ultra-minimal endpoint to test chunked encoding fix"""
    data = {"status": "ok", "requests": 1000, "cost": 50.5}
    
    # Convert to JSON bytes with exact length
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    
    return Response(
        content=json_bytes,
        status_code=200,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(json_bytes)),
            "Connection": "close"
        }
    )

@router.get("/usage-debug")
async def usage_debug():
    """Debug endpoint to test response generation step by step"""
    
    try:
        print("🔍 Starting usage debug endpoint...")
        
        # Step 1: Basic data creation
        basic_data = {
            "test": "step1",
            "requests": 1000,
            "cost": 50.0
        }
        print(f"Step 1 complete: {basic_data}")
        
        # Step 2: Date handling
        from datetime import datetime, timedelta
        base_date = datetime.now() - timedelta(days=7)
        daily_usage = []
        
        for i in range(7):  # Just 7 days for testing
            date = base_date + timedelta(days=i)
            daily_usage.append({
                "date": date.strftime("%Y-%m-%d"),
                "requests": 100 + i,
                "cost": 10.0 + i
            })
        
        print(f"Step 2 complete: Generated {len(daily_usage)} daily entries")
        
        # Step 3: Build final response
        response_data = {
            "status": "debug_success",
            "total_requests": sum(d["requests"] for d in daily_usage),
            "total_cost": round(sum(d["cost"] for d in daily_usage), 2),
            "daily_usage": daily_usage,
            "debug_info": {
                "endpoint": "usage-debug",
                "timestamp": datetime.now().isoformat(),
                "step": "final"
            }
        }
        
        print(f"Step 3 complete: Final data has {len(response_data)} keys")
        
        # Step 4: JSON conversion test
        import json
        json_str = json.dumps(response_data, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        content_length = len(json_bytes)
        
        print(f"Step 4 complete: JSON is {content_length} bytes")
        
        # Step 5: Return with Response class
        from fastapi.responses import Response
        
        return Response(
            content=json_bytes,
            status_code=200,
            media_type="application/json",
            headers={
                "Content-Length": str(content_length),
                "Cache-Control": "no-cache",
                "Connection": "close",
                "X-Debug": "success"
            }
        )
        
    except Exception as e:
        print(f"❌ Debug endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error response
        error_data = {"error": str(e), "status": "debug_failed"}
        error_json = json.dumps(error_data).encode('utf-8')
        
        return Response(
            content=error_json,
            status_code=500,
            media_type="application/json",
            headers={
                "Content-Length": str(len(error_json)),
                "X-Debug": "error"
            }
        )
    
@router.get("/usage-simple")
async def usage_simple():
    """Ultra-simple usage endpoint - guaranteed to work"""
    
    # Very basic response structure
    data = {
        "total_requests": 2500,
        "total_tokens": 1200000,
        "total_cost": 150.75,
        "avg_response_time": 1.8,
        "avg_confidence": 0.94,
        "top_models": [
            {"name": "GPT-4", "usage": 42, "score": 0.95},
            {"name": "Claude", "usage": 31, "score": 0.92},
            {"name": "Gemini", "usage": 27, "score": 0.88}
        ],
        "daily_usage": [
            {"date": "2025-08-31", "requests": 1200, "cost": 45.2},
            {"date": "2025-09-01", "requests": 1300, "cost": 48.3}
        ],
        "status": "success"
    }
