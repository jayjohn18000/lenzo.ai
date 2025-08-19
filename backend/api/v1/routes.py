# backend/api/v1/routes.py
"""
Revenue-focused API routes for NextAGI with comprehensive tracking,
billing integration, and enterprise features.
"""

import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.api_key import verify_api_key, get_api_manager, APIKeyManager
from backend.judge.model_selector import select_models_for_request, get_query_analysis, estimate_cost
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions
from backend.judge.steps.enhanced_scoring import enhanced_consensus_selection
from backend.database import get_db
import json

# Request/Response Models
class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    mode: str = Field(default="balanced", regex="^(speed|quality|balanced|cost)$")
    max_models: int = Field(default=4, ge=1, le=8)
    custom_models: Optional[List[str]] = None
    budget_limit: Optional[float] = Field(None, ge=0, le=10.0)
    include_reasoning: bool = True
    output_format: str = Field(default="markdown", regex="^(markdown|json)$")
    stream_response: bool = False

class QueryResponse(BaseModel):
    request_id: str
    answer: str
    confidence: float
    models_used: List[str]
    winner_model: str
    response_time_ms: int
    estimated_cost: float
    reasoning: Optional[str] = None
    trust_metrics: Optional[Dict[str, float]] = None

class BatchRequest(BaseModel):
    queries: List[QueryRequest] = Field(..., max_items=10)
    parallel_processing: bool = True

class UsageStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    avg_confidence: float
    top_models: List[Dict[str, Any]]
    daily_usage: List[Dict[str, Any]]

# Router setup
router = APIRouter(prefix="/api/v1", tags=["NextAGI Core"])

@router.post("/query", response_model=QueryResponse)
async def query_models(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    key_info: Dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Main query endpoint - routes prompt to optimal models and returns best answer.
    Includes comprehensive usage tracking for billing and analytics.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Get API manager for usage tracking
        api_manager = APIKeyManager(db)
        
        # Select optimal models based on query
        if request.custom_models:
            selected_models = request.custom_models[:request.max_models]
        else:
            selected_models = select_models_for_request(
                request.prompt, 
                request.mode, 
                request.max_models,
                request.budget_limit
            )
        
        # Estimate cost before proceeding
        cost_estimate = estimate_cost(selected_models, request.prompt)
        estimated_cost = cost_estimate["total_estimated_cost"]
        
        # Check user's tier limits
        user_tier = key_info["subscription_tier"]
        if user_tier == "free" and len(selected_models) > 2:
            selected_models = selected_models[:2]  # Limit free tier
        
        # Build route request
        route_req = RouteRequest(
            prompt=request.prompt,
            options=RouteOptions(
                models=selected_models,
                model_selection_mode=request.mode,
                output_format=request.output_format,
                require_citations=True
            )
        )
        
        # Execute the routing pipeline
        result = await run_pipeline("judge", route_req, trace_id=request_id)
        
        # Enhanced consensus selection with trust metrics
        from backend.judge.steps.fanout import fanout_generate
        from backend.judge.steps.llm_as_judge import judge_candidates
        
        # Get candidates and judge scores for enhanced selection
        candidates = await fanout_generate(request.prompt, selected_models, request_id, request.mode)
        judge_scores = await judge_candidates(candidates, route_req, request_id)
        
        # Apply enhanced scoring
        winner_candidate, trust_metrics, confidence, explanation = await enhanced_consensus_selection(
            candidates, judge_scores
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Track usage in background
        background_tasks.add_task(
            api_manager.track_usage,
            user_id=key_info["user_id"],
            api_key_id=key_info["api_key_id"],
            request_id=request_id,
            models_attempted=selected_models,
            models_succeeded=[c.model for c in candidates if c.text],
            winner_model=winner_candidate.model,
            total_tokens=cost_estimate["estimated_tokens"],
            response_time_ms=response_time_ms,
            confidence_score=confidence
        )
        
        # Prepare response
        response = QueryResponse(
            request_id=request_id,
            answer=winner_candidate.text,
            confidence=confidence,
            models_used=selected_models,
            winner_model=winner_candidate.model,
            response_time_ms=response_time_ms,
            estimated_cost=estimated_cost,
            reasoning=explanation if request.include_reasoning else None,
            trust_metrics=trust_metrics if request.include_reasoning else None
        )
        
        return response
        
    except Exception as e:
        # Log error and return appropriate response
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.post("/batch", response_model=List[QueryResponse])
async def batch_query(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
    key_info: Dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Batch processing endpoint for enterprise users.
    Processes multiple queries efficiently with optional parallel execution.
    """
    # Check tier permissions
    if key_info["subscription_tier"] == "free":
        raise HTTPException(status_code=403, detail="Batch processing requires paid subscription")
    
    if len(request.queries) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 queries per batch")
    
    results = []
    
    if request.parallel_processing and key_info["subscription_tier"] in ["professional", "enterprise"]:
        # Parallel processing for higher tiers
        import asyncio
        tasks = []
        for query in request.queries:
            task = query_models(query, background_tasks, key_info, db)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                results[i] = QueryResponse(
                    request_id=str(uuid.uuid4()),
                    answer=f"Error processing query {i+1}: {str(result)}",
                    confidence=0.0,
                    models_used=[],
                    winner_model="error",
                    response_time_ms=0,
                    estimated_cost=0.0
                )
    else:
        # Sequential processing
        for query in request.queries:
            try:
                result = await query_models(query, background_tasks, key_info, db)
                results.append(result)
            except Exception as e:
                results.append(QueryResponse(
                    request_id=str(uuid.uuid4()),
                    answer=f"Error: {str(e)}",
                    confidence=0.0,
                    models_used=[],
                    winner_model="error",
                    response_time_ms=0,
                    estimated_cost=0.0
                ))
    
    return results

@router.get("/analyze", response_model=Dict[str, Any])
async def analyze_query(
    prompt: str = Query(..., min_length=1),
    key_info: Dict = Depends(verify_api_key)
):
    """
    Analyze query and provide model recommendations without executing.
    Useful for cost estimation and optimization.
    """
    analysis = get_query_analysis(prompt)
    cost_estimates = {}
    
    for mode, recommendation in analysis["recommendations"].items():
        cost_estimates[mode] = estimate_cost(recommendation["models"], prompt)
    
    return {
        **analysis,
        "cost_estimates": cost_estimates
    }

@router.get("/usage", response_model=UsageStats)
async def get_usage_statistics(
    days: int = Query(default=30, ge=1, le=365),
    key_info: Dict = Depends(verify_api_key),
    api_manager: APIKeyManager = Depends(get_api_manager)
):
    """Get detailed usage statistics for the authenticated user"""
    stats = await api_manager.get_usage_stats(key_info["user_id"], days)
    return UsageStats(**stats)

@router.get("/models", response_model=Dict[str, Any])
async def list_available_models(key_info: Dict = Depends(verify_api_key)):
    """List available models with capabilities and pricing"""
    from backend.judge.model_selector import SmartModelSelector
    
    selector = SmartModelSelector()
    models_info = {}
    
    for model_name, specs in selector.model_specs.items():
        # Filter model access based on subscription tier
        tier = key_info["subscription_tier"]
        if tier == "free" and specs.cost_per_1k_tokens > 0.001:
            continue  # Hide expensive models for free tier
        
        models_info[model_name] = {
            "cost_per_1k_tokens": specs.cost_per_1k_tokens,
            "avg_response_time_ms": specs.avg_response_time_ms,
            "quality_score": specs.quality_score,
            "strengths": [s.value for s in specs.strengths],
            "context_window": specs.context_window,
            "supports_function_calling": specs.supports_function_calling,
            "supports_vision": specs.supports_vision
        }
    
    return {
        "available_models": models_info,
        "subscription_tier": key_info["subscription_tier"],
        "tier_limits": {
            "max_models_per_query": 8 if tier == "enterprise" else 4 if tier == "professional" else 2,
            "batch_processing": tier != "free",
            "parallel_processing": tier in ["professional", "enterprise"]
        }
    }

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@router.post("/feedback")
async def submit_feedback(
    request_id: str,
    rating: int = Field(..., ge=1, le=5),
    feedback: Optional[str] = None,
    key_info: Dict = Depends(verify_api_key),
    api_manager: APIKeyManager = Depends(get_api_manager)
):
    """Submit feedback for a specific query result"""
    # Store feedback for model improvement
    feedback_data = {
        "request_id": request_id,
        "user_id": key_info["user_id"],
        "rating": rating,
        "feedback": feedback,
        "timestamp": datetime.utcnow()
    }
    
    # This would integrate with your feedback storage system
    # For now, we'll just acknowledge receipt
    
    return {
        "message": "Feedback received",
        "request_id": request_id,
        "rating": rating
    }

# Streaming endpoint for real-time responses
@router.post("/stream")
async def stream_query(
    request: QueryRequest,
    key_info: Dict = Depends(verify_api_key)
):
    """
    Streaming endpoint that returns results as they become available.
    Useful for UI responsiveness with longer queries.
    """
    if key_info["subscription_tier"] == "free":
        raise HTTPException(status_code=403, detail="Streaming requires paid subscription")
    
    async def generate_stream():
        # Start processing
        yield f"data: {json.dumps({'status': 'started', 'message': 'Processing query...'})}\n\n"
        
        # Select models
        selected_models = select_models_for_request(request.prompt, request.mode, request.max_models)
        yield f"data: {json.dumps({'status': 'models_selected', 'models': selected_models})}\n\n"
        
        # Process query (simplified for demo)
        try:
            # This would integrate with your actual streaming pipeline
            time.sleep(2)  # Simulate processing
            
            result = {
                "status": "completed",
                "answer": "This would be the actual streamed result...",
                "confidence": 0.92,
                "winner_model": selected_models[0]
            }
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            error_result = {"status": "error", "message": str(e)}
            yield f"data: {json.dumps(error_result)}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/plain")

# Enterprise-specific endpoints
@router.get("/enterprise/analytics", response_model=Dict[str, Any])
async def enterprise_analytics(
    key_info: Dict = Depends(verify_api_key),
    api_manager: APIKeyManager = Depends(get_api_manager)
):
    """Advanced analytics for enterprise customers"""
    if key_info["subscription_tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise subscription required")
    
    # Get comprehensive analytics
    stats = await api_manager.get_usage_stats(key_info["user_id"], 90)
    
    # Add enterprise-specific metrics
    enterprise_metrics = {
        "cost_optimization_suggestions": [],
        "model_performance_trends": {},
        "usage_patterns": {},
        "roi_metrics": {}
    }
    
    return {
        "basic_stats": stats,
        "enterprise_metrics": enterprise_metrics
    }