# backend/judge/pipelines/runner.py - CREATE THIS FILE
from typing import Dict, Any
import logging
from backend.judge.schemas import RouteRequest
from backend.judge.pipelines.judge import run_judge

logger = logging.getLogger(__name__)

async def run_pipeline(pipeline_id: str, req: RouteRequest, trace_id: str) -> Dict[str, Any]:
    """
    Route request to appropriate pipeline and return standardized results.
    
    Args:
        pipeline_id: "judge" or "tool_chain" 
        req: The route request
        trace_id: Tracing identifier
        
    Returns:
        Dict with standardized response fields
    """
    logger.info(f"[{trace_id}] Running pipeline: {pipeline_id}")
    
    if pipeline_id == "judge":
        return await run_judge(req, trace_id)
    elif pipeline_id == "tool_chain":
        # For now, fall back to judge pipeline until tool_chain is implemented
        logger.info(f"[{trace_id}] tool_chain not implemented, falling back to judge")
        return await run_judge(req, trace_id)
    else:
        raise ValueError(f"Unknown pipeline: {pipeline_id}")


# For future tool_chain implementation:
async def run_tool_chain(req: RouteRequest, trace_id: str) -> Dict[str, Any]:
    """
    Tool-chain pipeline for fact-checking and verification.
    TODO: Implement when needed for advanced fact-checking.
    """
    # Placeholder - implement when needed
    logger.warning(f"[{trace_id}] tool_chain pipeline not yet implemented")
    
    # For now, return a simple response
    return {
        "answer": "Tool chain pipeline not yet implemented. Using judge pipeline instead.",
        "winner_model": "system",
        "confidence": 0.5,
        "scores_by_trait": {"accuracy": 0.5},
        "citations": [],
        "models_attempted": [],
        "models_succeeded": [],
    }