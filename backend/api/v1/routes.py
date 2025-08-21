# backend/api/v1/routes.py
"""
Simplified API routes for NextAGI MVP - focused on core functionality.
"""

import time
import uuid
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions

# Simplified Request/Response Models
class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    mode: str = Field(default="balanced", pattern="^(speed|quality|balanced)$")
    max_models: int = Field(default=3, ge=1, le=5)

class QueryResponse(BaseModel):
    request_id: str
    answer: str
    confidence: float
    winner_model: str
    response_time_ms: int
    models_used: list[str]

# Router setup
router = APIRouter(prefix="/api/v1", tags=["NextAGI Core"])

# Simplified model selection based on mode
def get_models_for_mode(mode: str, max_models: int) -> list[str]:
    """Simple model selection based on query mode"""
    model_pools = {
        "speed": ["gpt-3.5-turbo", "claude-3-haiku-20240307"],
        "balanced": ["gpt-4o-mini", "claude-3-5-sonnet-20241022", "gpt-3.5-turbo"],
        "quality": ["gpt-4o", "claude-3-5-sonnet-20241022", "gpt-4-turbo-preview"]
    }
    
    models = model_pools.get(mode, model_pools["balanced"])
    return models[:max_models]

@router.post("/query", response_model=QueryResponse)
async def query_models(request: QueryRequest):
    """
    Main query endpoint - routes prompt to models and returns best answer.
    Simplified version without auth/billing for MVP.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Select models based on mode
        selected_models = get_models_for_mode(request.mode, request.max_models)
        
        # Build route request
        route_req = RouteRequest(
            prompt=request.prompt,
            options=RouteOptions(
                models=selected_models,
                model_selection_mode=request.mode,
                require_citations=True
            )
        )
        
        # Execute the routing pipeline
        result = await run_pipeline("judge", route_req, trace_id=request_id)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        response = QueryResponse(
            request_id=request_id,
            answer=result.get("answer", "No answer generated"),
            confidence=result.get("confidence", 0.0),
            winner_model=result.get("winner_model", "unknown"),
            response_time_ms=response_time_ms,
            models_used=result.get("models_attempted", selected_models)
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "0.1.0-mvp"
    }

@router.get("/models")
async def list_available_models():
    """List available models for the UI"""
    return {
        "modes": {
            "speed": {
                "description": "Fast responses, lower cost",
                "models": ["gpt-3.5-turbo", "claude-3-haiku-20240307"],
                "typical_response_time": "1-2 seconds"
            },
            "balanced": {
                "description": "Good balance of speed and quality",
                "models": ["gpt-4o-mini", "claude-3-5-sonnet-20241022", "gpt-3.5-turbo"],
                "typical_response_time": "2-4 seconds"
            },
            "quality": {
                "description": "Best quality, slower responses",
                "models": ["gpt-4o", "claude-3-5-sonnet-20241022", "gpt-4-turbo-preview"],
                "typical_response_time": "3-6 seconds"
            }
        }
    }