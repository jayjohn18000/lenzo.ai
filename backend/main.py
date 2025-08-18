# backend/main.py
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.judge.schemas import RouteRequest, RouteResponse, HealthResponse
from backend.judge.config import settings
from backend.judge.policy.dispatcher import decide_pipeline
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.utils.trace import new_trace_id
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TruthRouter",
    version="0.1.0",
    description="Multi-LLM truth routing with evaluation metrics"
)

# CORS for local dev / Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Lightweight readiness check with model availability."""
    ok = bool(settings.OPENROUTER_API_KEY)
    available_models = len(settings.DEFAULT_MODELS) if ok else 0
    
    return HealthResponse(
        status="ok" if ok else "degraded",
        available_models=available_models,
        last_test_time=None  # Could track last successful test
    )


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    """
    Unified entrypoint with comprehensive metrics:
      - decide pipeline (judge | tool_chain)
      - run selected pipeline
      - return normalized response with trace_id and all metrics
    """
    trace_id = new_trace_id()
    start_time = time.perf_counter()
    
    logger.info(f"[{trace_id}] Starting route request for prompt: {req.prompt[:100]}...")
    
    try:
        # Decide which pipeline to use
        pipeline_id, decision_reason = decide_pipeline(req)
        logger.info(f"[{trace_id}] Selected pipeline: {pipeline_id} (reason: {decision_reason})")
        
        # Run the pipeline and get results
        result = await run_pipeline(pipeline_id, req, trace_id=trace_id)

        # Ensure all required fields are present
        result.setdefault("citations", [])
        result.setdefault("models_attempted", [])
        result.setdefault("models_succeeded", [])
        result.setdefault("response_time_ms", int((time.perf_counter() - start_time) * 1000))
        
        # Ensure scores_by_trait is properly formatted
        if result.get("scores_by_trait"):
            result["scores_by_trait"] = {
                str(k): float(v) if v is not None else 0.0 
                for k, v in result["scores_by_trait"].items()
            }
        
        # Ensure confidence is a float
        if result.get("confidence") is not None:
            result["confidence"] = float(result["confidence"])
        
        logger.info(f"[{trace_id}] Request completed successfully in {result['response_time_ms']}ms")
        logger.info(f"[{trace_id}] Models succeeded: {result.get('models_succeeded', [])}")
        
        return RouteResponse(
            trace_id=trace_id,
            pipeline_id=pipeline_id,
            decision_reason=decision_reason,
            answer=result.get("answer", ""),
            winner_model=result.get("winner_model"),
            confidence=result.get("confidence"),
            response_time_ms=result.get("response_time_ms"),
            models_attempted=result.get("models_attempted", []),
            models_succeeded=result.get("models_succeeded", []),
            scores_by_trait=result.get("scores_by_trait"),
            evidence=result.get("evidence"),
            citations=result.get("citations", []),
        )
        
    except HTTPException:
        # re-raise FastAPI HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Error processing request: {str(e)}", exc_info=True)
        # one consistent error envelope
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "trace_id": trace_id},
        )


# Add some example endpoints for testing
@app.get("/test-models")
async def test_models():
    """Test endpoint to check which models are configured and working"""
    return {
        "default_models": settings.DEFAULT_MODELS,
        "judge_model": settings.JUDGE_MODEL,
        "fallback_models": settings.FALLBACK_MODELS,
        "speed_optimized": settings.SPEED_OPTIMIZED_MODELS,
        "quality_optimized": settings.QUALITY_OPTIMIZED_MODELS,
        "cost_optimized": settings.COST_OPTIMIZED_MODELS,
    }


# optional: `uvicorn backend.main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)