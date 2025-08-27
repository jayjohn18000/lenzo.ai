# backend/judge/pipelines/judge.py
"""
Judge pipeline - Main orchestrator for multi-LLM consensus judging
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from backend.judge.schemas import RouteRequest, Candidate
from backend.judge.steps.fanout import fanout_generate
from backend.judge.steps.heuristics import score_heuristics
from backend.judge.steps.llm_as_judge import judge_candidates
from backend.judge.steps.consensus import ensemble_consensus
from backend.judge.steps.consensus_enhanced import ensemble_consensus_enhanced
from backend.judge.steps.rank_select import rank_and_select
from backend.judge.utils.citations import extract_citations, inject_citations

logger = logging.getLogger(__name__)

async def run_judge(req: RouteRequest, trace_id: str) -> Dict[str, Any]:
    """
    Main judge pipeline orchestrator with performance optimizations
    
    Flow:
    1. Generate candidates via fanout
    2. Apply heuristic scoring
    3. Judge candidates with LLM
    4. Reach consensus
    5. Select winner and calculate confidence
    6. Extract citations if needed
    """
    start_time = time.perf_counter()
    logger.info(f"[{trace_id}] Starting judge pipeline")
    
    try:
        # Step 1: Parallel candidate generation with early setup
        candidates_task = asyncio.create_task(
            fanout_generate(
                req.prompt,
                req.options.models,
                trace_id,
                req.options.model_selection_mode
            )
        )
        
        # Pre-compile citation extraction regex while waiting
        citation_extractor = asyncio.create_task(
            asyncio.to_thread(lambda: compile_citation_patterns())
        ) if req.options.require_citations else None
        
        # Wait for candidates
        candidates = await candidates_task
        
        if not candidates:
            logger.error(f"[{trace_id}] No candidates generated")
            return _error_response("No models available", trace_id)
        
        logger.info(f"[{trace_id}] Generated {len(candidates)} candidates")
        
        # Step 2: Quick heuristic filtering (parallel with judge prep)
        heuristics_task = asyncio.create_task(
            asyncio.to_thread(score_heuristics, candidates)
        )
        
        # Step 3: Judge candidates (main bottleneck - needs optimization)
        judge_scores = await judge_candidates(candidates, req, trace_id)
        
        # Wait for heuristics to complete
        candidates_with_heuristics = await heuristics_task
        
        # Step 4: Ensemble consensus
        winner_idx, consensus_score = ensemble_consensus(judge_scores)
        
        if winner_idx < 0:
            logger.error(f"[{trace_id}] Consensus failed")
            return _error_response("Consensus failed", trace_id)
        
        # Step 5: Final selection and confidence calculation
        winner, scores_by_trait, confidence = rank_and_select(
            candidates_with_heuristics,
            judge_scores,
            (winner_idx, consensus_score)
        )
        
        # Step 6: Citation handling if required
        citations = []
        if req.options.require_citations and citation_extractor:
            await citation_extractor  # Ensure patterns are ready
            citations = extract_citations(winner.text)
            if citations and req.options.output_format == "markdown":
                winner.text = inject_citations(winner.text, citations)
        
        # Build response
        end_time = time.perf_counter()
        response_time_ms = int((end_time - start_time) * 1000)
        
        result = {
            "answer": winner.text,
            "winner_model": winner.model,
            "confidence": confidence,
            "scores_by_trait": scores_by_trait,
            "citations": citations,
            "models_attempted": [c.model for c in candidates],
            "models_succeeded": [c.model for c in candidates if c.text],
            "response_time_ms": response_time_ms,
            "pipeline_id": "judge",
            "trace_id": trace_id
        }
        
        # Log performance metrics
        _log_performance_metrics(candidates, response_time_ms, trace_id)
        
        return result
        
    except Exception as e:
        logger.error(f"[{trace_id}] Pipeline failed: {str(e)}")
        return _error_response(str(e), trace_id)


def _error_response(error_msg: str, trace_id: str) -> Dict[str, Any]:
    """Build error response"""
    return {
        "answer": f"Error: {error_msg}",
        "winner_model": "none",
        "confidence": 0.0,
        "scores_by_trait": {},
        "citations": [],
        "models_attempted": [],
        "models_succeeded": [],
        "error": error_msg,
        "pipeline_id": "judge",
        "trace_id": trace_id
    }


def _log_performance_metrics(
    candidates: List[Candidate], 
    total_time_ms: int, 
    trace_id: str
):
    """Log detailed performance metrics"""
    model_times = {c.model: c.gen_time_ms for c in candidates}
    avg_model_time = sum(model_times.values()) / len(model_times) if model_times else 0
    
    logger.info(
        f"[{trace_id}] Performance summary: "
        f"total={total_time_ms}ms, "
        f"avg_model={avg_model_time:.0f}ms, "
        f"models={len(candidates)}, "
        f"slowest={max(model_times.values()) if model_times else 0}ms"
    )


def compile_citation_patterns():
    """Pre-compile citation regex patterns"""
    import re
    patterns = [
        re.compile(r'\[(\d+)\]'),
        re.compile(r'https?://[^\s]+'),
        re.compile(r'\(([^)]+, \d{4})\)')
    ]
    return patterns


# Enhanced version with early termination
async def run_judge_optimized(req: RouteRequest, trace_id: str) -> Dict[str, Any]:
    """
    Optimized judge pipeline with early termination and caching
    """
    start_time = time.perf_counter()
    logger.info(f"[{trace_id}] Starting optimized judge pipeline")
    
    # Check if we can use fast path
    if _can_use_fast_path(req):
        return await _fast_path_judge(req, trace_id)
    
    # Otherwise use full pipeline
    return await run_judge(req, trace_id)


def _can_use_fast_path(req: RouteRequest) -> bool:
    """Determine if we can use simplified fast path"""
    # Fast path for simple queries without special requirements
    return (
        len(req.prompt) < 100 and
        not req.expected_traits and
        req.options.model_selection_mode == "speed" and
        not req.options.require_citations
    )


async def _fast_path_judge(req: RouteRequest, trace_id: str) -> Dict[str, Any]:
    """Fast path for simple queries - single model, no judging"""
    logger.info(f"[{trace_id}] Using fast path")
    
    # Use only fastest model
    fast_model = "openai/gpt-3.5-turbo"
    candidates = await fanout_generate(req.prompt, [fast_model], trace_id, "speed")
    
    if not candidates:
        return _error_response("Fast model unavailable", trace_id)
    
    winner = candidates[0]
    
    return {
        "answer": winner.text,
        "winner_model": winner.model,
        "confidence": 0.85,  # Fixed confidence for fast path
        "scores_by_trait": {"speed": 1.0},
        "citations": [],
        "models_attempted": [fast_model],
        "models_succeeded": [fast_model] if winner.text else [],
        "response_time_ms": winner.gen_time_ms,
        "pipeline_id": "judge_fast",
        "trace_id": trace_id
    }