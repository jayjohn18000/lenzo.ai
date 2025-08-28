# backend/api/v1/routes.py (UPDATED - With Real Data & Bounds Checking)

import time
import uuid
import random
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from statistics import mean
import logging

# Import your existing pipeline components
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions, Candidate
from backend.judge.utils.cache import get_cache

# Import database models
from backend.database import get_db, QueryRequest as DBQueryRequest, ModelResponse as DBModelResponse

logger = logging.getLogger(__name__)

# Define all required Pydantic models (keep existing ones)
class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    prompt: str = Field(..., min_length=1, max_length=5000)
    mode: str = Field(default="balanced", pattern="^(speed|quality|balanced|cost)$")
    max_models: int = Field(default=3, ge=1, le=5)
    budget_limit: Optional[float] = Field(default=None, ge=0)
    include_reasoning: bool = Field(default=True)

class ModelMetrics(BaseModel):
    """Individual model response details for frontend display"""
    model: str
    response: str
    confidence: float = Field(ge=0.0, le=1.0)  # Enforced at model level
    response_time_ms: int
    tokens_used: int
    cost: float
    reliability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    consistency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    trait_scores: Dict[str, float] = {}
    rank_position: int = 1
    is_winner: bool = False
    error: Optional[str] = None

class ModelComparison(BaseModel):
    """Side-by-side comparison data"""
    best_confidence: float = Field(ge=0.0, le=1.0)
    worst_confidence: float = Field(ge=0.0, le=1.0)
    avg_response_time: int
    total_cost: float
    performance_spread: float = Field(ge=0.0, le=1.0)
    model_count: int

class QueryResponse(BaseModel):
    """Enhanced response with complete model data"""
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

# Router setup
router = APIRouter(prefix="/api/v1", tags=["NextAGI Core"])

# Confidence validation helper
def validate_confidence(value: float, source: str = "") -> float:
    """Ensure confidence is within [0, 1] bounds"""
    if value < 0:
        logger.warning(f"Negative confidence {value} from {source}, setting to 0")
        return 0.0
    elif value > 1:
        logger.warning(f"Confidence {value} exceeds 1.0 from {source}, capping at 1.0")
        return 1.0
    return value

# Model selection function (keep existing)
def get_models_for_mode(mode: str, max_models: int, prompt: str = "") -> List[str]:
    """Smart model selection based on query mode and content analysis"""
    model_pools = {
        "speed": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
        "quality": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus"],
        "balanced": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
        "cost": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"]
    }
    
    selected = model_pools.get(mode, model_pools["balanced"])
    return selected[:max_models]

# Cost estimation function (keep existing)
def estimate_token_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost based on model and token usage"""
    cost_map = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
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

# Calculate confidence with proper bounds
def calculate_model_confidence(
    candidate: 'Candidate',
    judge_scores: Optional[Dict[str, float]] = None,
    is_winner: bool = False
) -> float:
    """Calculate bounded confidence score for a model response"""
    base_confidence = 0.7
    
    # Text quality assessment
    if hasattr(candidate, 'text') and candidate.text:
        text_length = len(candidate.text.split())
        if 20 <= text_length <= 500:
            base_confidence += 0.1
        elif text_length < 20:
            base_confidence -= 0.2
        elif text_length > 1000:
            base_confidence -= 0.05
    
    # Response time factor
    if hasattr(candidate, 'gen_time_ms') and candidate.gen_time_ms:
        if candidate.gen_time_ms < 2000:
            base_confidence += 0.05
        elif candidate.gen_time_ms > 5000:
            base_confidence -= 0.1
    
    # Apply judge scores if available
    if judge_scores:
        judge_avg = mean(judge_scores.values())
        # Weighted average with base confidence
        base_confidence = (base_confidence * 0.4 + judge_avg * 0.6)
    
    # Winner boost (carefully bounded)
    if is_winner:
        # Only boost if there's room below 1.0
        max_boost = min(0.05, 1.0 - base_confidence)
        base_confidence += max_boost
    
    # Final bounds check
    return validate_confidence(base_confidence, f"model:{getattr(candidate, 'model', 'unknown')}")

# Main query endpoint - WITH REAL DATA STORAGE
@router.post("/query", response_model=QueryResponse)
async def query_models(request: QueryRequest):
    """
    Enhanced main query endpoint with real data storage and bounded confidence
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Define selected_models BEFORE using it
    selected_models = get_models_for_mode(request.mode, request.max_models, request.prompt)
    
    # Check cache
    try:
        cache = await get_cache()
        cached_result = await cache.get(
            request.prompt,
            selected_models,
            mode=request.mode
        )
        
        if cached_result:
            # Validate cached confidence values
            if 'confidence' in cached_result:
                cached_result['confidence'] = validate_confidence(cached_result['confidence'])
            return QueryResponse(**cached_result)
    except Exception as cache_error:
        logger.warning(f"Cache error: {cache_error}")
    
    # Initialize database session
    with get_db() as db:
        try:
            # Build route request for pipeline
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
            
            # Extract candidates and scores from pipeline result
            candidates = result.get("candidates", [])
            judge_scores = result.get("judge_scores", {})
            winner_idx = result.get("winner_idx", 0)
            
            # Process and store real model responses
            model_metrics = []
            total_cost = 0.0
            total_tokens = 0
            
            # Create database query request
            db_query = DBQueryRequest(
                request_id=request_id,
                prompt=request.prompt,
                mode=request.mode,
                max_models=request.max_models,
                response_time_ms=response_time_ms
            )
            
            # Process each candidate
            for i, candidate in enumerate(candidates):
                is_winner = (i == winner_idx)
                
                # Calculate bounded confidence
                candidate_scores = judge_scores.get(i, {})
                confidence = calculate_model_confidence(candidate, candidate_scores, is_winner)
                
                # Estimate cost
                tokens_used = getattr(candidate, 'num_tokens', 200)
                cost = estimate_token_cost(
                    candidate.model,
                    tokens_used // 2,
                    tokens_used // 2
                )
                
                total_cost += cost
                total_tokens += tokens_used
                
                # Extract scores with validation
                reliability = validate_confidence(candidate_scores.get('reliability', 0.8))
                consistency = validate_confidence(candidate_scores.get('consistency', 0.75))
                hallucination_risk = validate_confidence(candidate_scores.get('hallucination_risk', 0.15))
                citation_quality = validate_confidence(candidate_scores.get('citation_quality', 0.7))
                
                # Validate trait scores
                trait_scores = {}
                for trait, score in candidate_scores.items():
                    if trait not in ['reliability', 'consistency', 'hallucination_risk', 'citation_quality']:
                        trait_scores[trait] = validate_confidence(score)
                
                # Create metrics object
                metric = ModelMetrics(
                    model=candidate.model,
                    response=candidate.text,
                    confidence=confidence,
                    response_time_ms=getattr(candidate, 'gen_time_ms', 1500),
                    tokens_used=tokens_used,
                    cost=cost,
                    reliability_score=reliability,
                    consistency_score=consistency,
                    hallucination_risk=hallucination_risk,
                    citation_quality=citation_quality,
                    trait_scores=trait_scores,
                    rank_position=i + 1,
                    is_winner=is_winner,
                    error=getattr(candidate, 'error', None)
                )
                
                model_metrics.append(metric)
                
                # Store in database
                db_response = DBModelResponse(
                    request_id=request_id,
                    model_name=candidate.model,
                    response_text=candidate.text,
                    confidence_score=confidence,
                    response_time_ms=metric.response_time_ms,
                    tokens_used=tokens_used,
                    cost=cost,
                    reliability_score=reliability,
                    consistency_score=consistency,
                    hallucination_risk=hallucination_risk,
                    citation_quality=citation_quality,
                    rank_position=i + 1,
                    is_winner=is_winner,
                    error_message=metric.error
                )
                db_response.trait_scores = trait_scores
                db.add(db_response)
            
            # Sort by confidence and update rankings
            model_metrics.sort(key=lambda x: x.confidence, reverse=True)
            for i, metric in enumerate(model_metrics):
                metric.rank_position = i + 1
                metric.is_winner = (i == 0)
            
            # Update winner information
            winner = model_metrics[0] if model_metrics else None
            if winner:
                db_query.winner_model = winner.model
                db_query.winner_confidence = validate_confidence(winner.confidence)
            
            # Save query to database
            db_query.total_tokens_used = total_tokens
            db_query.total_cost = total_cost
            db_query.models_used = [m.model for m in model_metrics]
            db.add(db_query)
            db.commit()
            
            # Build comparison (with validated confidence)
            if model_metrics:
                confidences = [m.confidence for m in model_metrics]
                response_times = [m.response_time_ms for m in model_metrics]
                
                comparison = ModelComparison(
                    best_confidence=validate_confidence(max(confidences)),
                    worst_confidence=validate_confidence(min(confidences)),
                    avg_response_time=int(mean(response_times)),
                    total_cost=total_cost,
                    performance_spread=validate_confidence(max(confidences) - min(confidences)),
                    model_count=len(model_metrics)
                )
            else:
                comparison = None
            
            # Generate reasoning
            reasoning = generate_reasoning(model_metrics, winner, request.prompt) if request.include_reasoning else None
            
            # Build final response with validated confidence
            final_confidence = validate_confidence(result.get("confidence", 0.85))
            
            response = QueryResponse(
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
                scores_by_trait=result.get("scores_by_trait", {})
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            # Store failed request in database
            db.add(DBQueryRequest(
                request_id=request_id,
                prompt=request.prompt,
                mode=request.mode,
                max_models=request.max_models,
                response_time_ms=int((time.time() - start_time) * 1000),
                total_cost=0,
                winner_confidence=0,
                models_used=[]
            ))
            db.commit()
            
            raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

def generate_reasoning(
    metrics: List[ModelMetrics], 
    winner: Optional[ModelMetrics], 
    prompt: str
) -> str:
    """Generate reasoning with proper confidence bounds"""
    if not metrics:
        return "No models available for analysis"
    
    total_models = len(metrics)
    # All confidences are already validated
    avg_confidence = mean(m.confidence for m in metrics)
    avg_response_time = mean(m.response_time_ms for m in metrics)
    
    reasoning = f"""Multi-Model Analysis Results:

Query: "{prompt[:80]}..."

Winner: {winner.model if winner else 'Unknown'}
• Confidence: {winner.confidence:.1%}
• Response time: {winner.response_time_ms}ms
• Reliability: {winner.reliability_score:.1%}
• Hallucination risk: {winner.hallucination_risk:.1%}

Model Performance Summary:
• Models analyzed: {total_models}
• Average confidence: {avg_confidence:.1%}
• Average response time: {avg_response_time:.0f}ms

Complete Rankings:"""
    
    for metric in metrics:
        reasoning += f"\n{metric.rank_position}. {metric.model} - {metric.confidence:.1%}"
        if metric.error:
            reasoning += f" (Error: {metric.error})"
    
    return reasoning