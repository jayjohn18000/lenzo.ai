# backend/judge/pipelines/runner.py
"""
Main pipeline runner that orchestrates different execution strategies
"""

import time
import logging
from typing import Dict, Any
from backend.judge.schemas import RouteRequest, PipelineID
from backend.judge.pipelines.judge import run_judge
from backend.judge.pipelines.tool_chain import run_tool_chain
from backend.judge.policy.dispatcher import should_escalate_after_prepass

logger = logging.getLogger(__name__)

async def run_pipeline(
    pipeline_id: PipelineID,
    req: RouteRequest,
    trace_id: str
) -> Dict[str, Any]:
    """
    Execute the specified pipeline and return structured results
    """
    start_time = time.perf_counter()
    
    try:
        logger.info(f"[{trace_id}] Starting {pipeline_id} pipeline")
        
        if pipeline_id == "judge":
            result = await run_judge(req, trace_id)
            
            # Check if we should escalate to tool_chain based on confidence
            confidence = result.get("confidence", 0.0)
            if should_escalate_after_prepass(confidence, req):
                logger.info(f"[{trace_id}] Escalating to tool_chain (confidence: {confidence:.3f})")
                result = await run_tool_chain(req, trace_id)
                result["escalated"] = True
                
        elif pipeline_id == "tool_chain":
            result = await run_tool_chain(req, trace_id)
            
        else:
            raise ValueError(f"Unknown pipeline_id: {pipeline_id}")
        
        # Add common metadata
        end_time = time.perf_counter()
        result.update({
            "pipeline_id": pipeline_id,
            "response_time_ms": int((end_time - start_time) * 1000),
            "trace_id": trace_id
        })
        
        logger.info(f"[{trace_id}] Completed {pipeline_id} pipeline in {result['response_time_ms']}ms")
        return result
        
    except Exception as e:
        end_time = time.perf_counter()
        error_time = int((end_time - start_time) * 1000)
        logger.error(f"[{trace_id}] Pipeline {pipeline_id} failed after {error_time}ms: {e}")
        raise