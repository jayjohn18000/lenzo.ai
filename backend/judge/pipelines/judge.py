# backend/judge/pipelines/judge.py
"""
Enhanced judge pipeline with improved async processing and integration
"""

import sys
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from backend.judge.schemas import RouteRequest, Candidate
from backend.judge.config import settings  # ← FIXED: Added missing import
from backend.judge.steps.fanout import fanout_generate
from backend.judge.steps.heuristics import score_heuristics
from backend.judge.steps.llm_as_judge import judge_candidates
from backend.judge.steps.consensus import ensemble_consensus
from backend.judge.steps.rank_select import rank_and_select
from backend.judge.utils.citations import extract_citations

logger = logging.getLogger(__name__)

# Removed the overly aggressive circular import check that was causing issues
# if len([m for m in sys.modules if 'config' in m and m != __name__]) > 2:
#     raise ImportError(f"Potential circular import detected in {__name__}")

class JudgePipelineMetrics:
    """Track detailed metrics for the judge pipeline"""
    
    def __init__(self):
        self.step_timings = {}
        self.candidate_counts = {}
        self.model_performance = {}
    
    def record_step_timing(self, step_name: str, duration_ms: int):
        if step_name not in self.step_timings:
            self.step_timings[step_name] = []
        self.step_timings[step_name].append(duration_ms)
        
        # Keep only last 50 measurements
        if len(self.step_timings[step_name]) > 50:
            self.step_timings[step_name] = self.step_timings[step_name][-50:]
    
    def record_candidate_count(self, attempted: int, succeeded: int):
        self.candidate_counts[time.time()] = {"attempted": attempted, "succeeded": succeeded}
    
    def record_model_performance(self, model: str, response_time_ms: int, confidence: float):
        if model not in self.model_performance:
            self.model_performance[model] = []
        self.model_performance[model].append({
            "response_time_ms": response_time_ms,
            "confidence": confidence,
            "timestamp": time.time()
        })
        
        # Keep only last 20 measurements per model
        if len(self.model_performance[model]) > 20:
            self.model_performance[model] = self.model_performance[model][-20:]
    
    def get_step_stats(self, step_name: str) -> Dict[str, Any]:
        if step_name not in self.step_timings:
            return {"error": "No data"}
        
        timings = self.step_timings[step_name]
        return {
            "avg_ms": sum(timings) / len(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
            "count": len(timings)
        }

# Global metrics instance
judge_metrics = JudgePipelineMetrics()

async def run_judge(req: RouteRequest, trace_id: str) -> Dict:
    """
    Enhanced judge pipeline with comprehensive async optimization and metrics tracking:
      1) Optimized fan-out generation across models
      2) Parallel heuristic scoring
      3) Async LLM-as-Judge scoring per candidate (trait-based)
      4) Enhanced consensus selection
      5) Citation extraction with parallel processing
    """
    pipeline_start = time.perf_counter()
    
    logger.info(f"[{trace_id}] 🏛️ Starting enhanced judge pipeline")
    logger.info(f"[{trace_id}] 📋 Request: mode={req.options.model_selection_mode}, "
                f"models={req.options.models}, rubric={bool(req.options.rubric)}")
    
    # Step 1: Enhanced fan-out generation
    step_start = time.perf_counter()
    models = req.options.models or settings.get_models_for_mode(req.options.model_selection_mode)
    mode = req.options.model_selection_mode
    
    # Get model-specific timeout
    model_timeout = None
    if models and len(models) == 1:
        model_timeout = settings.get_model_timeout(models[0])
    
    # FIXED: Now the variables are properly defined before use
    candidates = await fanout_generate(req.prompt, models, trace_id, mode, model_timeout)
    
    fanout_time_ms = int((time.perf_counter() - step_start) * 1000)
    judge_metrics.record_step_timing("fanout", fanout_time_ms)
    
    logger.info(f"[{trace_id}] 📡 Fanout completed: {len(candidates)} candidates in {fanout_time_ms}ms")
    
    # Guard: if no candidates, fail gracefully
    if not candidates:
        logger.error(f"[{trace_id}] ❌ No candidates returned from fan-out generation")
        return {
            "answer": "I apologize, but I'm unable to process your request at the moment. Please try again later.",
            "winner_model": "error_fallback",
            "confidence": 0.0,
            "scores_by_trait": {},
            "citations": [],
            "models_attempted": models,
            "models_succeeded": [],
            "error": "no_candidates_generated"
        }
    
    # Track model performance
    models_attempted = list(set(c.model for c in candidates if c.model))
    models_succeeded = [c.model for c in candidates if c.text and len(c.text) > 0]
    
    judge_metrics.record_candidate_count(len(models_attempted), len(models_succeeded))
    
    # Record individual model performance
    for candidate in candidates:
        if candidate.model and candidate.gen_time_ms:
            # We'll calculate confidence later, for now use a placeholder
            judge_metrics.record_model_performance(
                candidate.model, 
                candidate.gen_time_ms, 
                candidate.heuristic_score or 0.5
            )
    
    logger.info(f"[{trace_id}] 📊 Models: {len(models_attempted)} attempted, {len(models_succeeded)} succeeded")
    
    # Step 2: Parallel heuristic scoring
    step_start = time.perf_counter()
    
    # Run heuristic scoring in thread pool for CPU-bound work
    with ThreadPoolExecutor(max_workers=min(len(candidates), 4)) as executor:
        # Split candidates into chunks for parallel processing
        chunk_size = max(1, len(candidates) // 4)
        chunks = [candidates[i:i + chunk_size] for i in range(0, len(candidates), chunk_size)]
        
        loop = asyncio.get_event_loop()
        heuristic_tasks = [
            loop.run_in_executor(executor, score_heuristics, chunk)
            for chunk in chunks
        ]
        
        scored_chunks = await asyncio.gather(*heuristic_tasks)
        
        # Flatten results
        candidates = []
        for chunk in scored_chunks:
            candidates.extend(chunk)
    
    heuristic_time_ms = int((time.perf_counter() - step_start) * 1000)
    judge_metrics.record_step_timing("heuristics", heuristic_time_ms)
    
    logger.info(f"[{trace_id}] 🎯 Heuristic scoring completed in {heuristic_time_ms}ms")
    
    # Step 3: Async LLM-as-Judge scoring
    step_start = time.perf_counter()
    
    try:
        judge_scores = await judge_candidates(candidates, req, trace_id)
    except Exception as e:
        logger.error(f"[{trace_id}] ❌ Judge scoring failed: {e}")
        # Fallback to heuristic scores only
        judge_scores = {
            i: {"overall": candidate.heuristic_score or 0.5}
            for i, candidate in enumerate(candidates)
        }
    
    judge_time_ms = int((time.perf_counter() - step_start) * 1000)
    judge_metrics.record_step_timing("judge_scoring", judge_time_ms)
    
    logger.info(f"[{trace_id}] ⚖️ Judge scoring completed in {judge_time_ms}ms")
    
    # Step 4: Enhanced consensus and selection
    step_start = time.perf_counter()
    
    # Use enhanced consensus if available, fallback to basic
    try:
        from backend.judge.steps.enhanced_scoring import enhanced_consensus_selection
        
        winner_candidate, trust_metrics, confidence, explanation = await enhanced_consensus_selection(
            candidates, judge_scores
        )
        
        # Extract additional metrics
        winner_idx = candidates.index(winner_candidate)
        avg_score = confidence  # Enhanced consensus provides final confidence
        scores_by_trait = trust_metrics or {}
        
        logger.info(f"[{trace_id}] 🧠 Enhanced consensus selected: {winner_candidate.model} "
                   f"(confidence: {confidence:.3f})")
        
    except ImportError:
        logger.warning(f"[{trace_id}] ⚠️ Enhanced scoring not available, using basic consensus")
        winner_idx, avg_score = ensemble_consensus(judge_scores)
        winner_candidate, scores_by_trait, confidence = rank_and_select(
            candidates, judge_scores, (winner_idx, avg_score)
        )
        trust_metrics = None
        explanation = None
    
    consensus_time_ms = int((time.perf_counter() - step_start) * 1000)
    judge_metrics.record_step_timing("consensus", consensus_time_ms)
    
    # Step 5: Async citation extraction
    step_start = time.perf_counter()
    
    # Extract citations asynchronously
    citations_task = asyncio.create_task(
        asyncio.to_thread(extract_citations, winner_candidate.text)
    )
    
    # While citations are being extracted, prepare other response data
    response_data = {
        "answer": winner_candidate.text,
        "winner_model": winner_candidate.model,
        "confidence": float(confidence),
        "models_attempted": models_attempted,
        "models_succeeded": models_succeeded,
    }
    
    # Wait for citations
    try:
        citations = await asyncio.wait_for(citations_task, timeout=2.0)  # 2 second timeout
        response_data["citations"] = citations
    except asyncio.TimeoutError:
        logger.warning(f"[{trace_id}] ⏰ Citation extraction timed out")
        response_data["citations"] = []
    except Exception as e:
        logger.error(f"[{trace_id}] ❌ Citation extraction failed: {e}")
        response_data["citations"] = []
    
    citation_time_ms = int((time.perf_counter() - step_start) * 1000)
    judge_metrics.record_step_timing("citations", citation_time_ms)
    
    # Ensure scores_by_trait has proper float values
    if scores_by_trait:
        scores_by_trait = {k: float(v) for k, v in scores_by_trait.items()}
    
    response_data["scores_by_trait"] = scores_by_trait or {}
    
    # Add enhanced metrics if available
    if trust_metrics:
        response_data["trust_metrics"] = trust_metrics
    if explanation:
        response_data["explanation"] = explanation
    
    # Calculate total pipeline time
    total_pipeline_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
    judge_metrics.record_step_timing("total_pipeline", total_pipeline_time_ms)
    
    # Log comprehensive performance summary
    logger.info(f"[{trace_id}] 🎉 Judge pipeline completed in {total_pipeline_time_ms}ms")
    logger.info(f"[{trace_id}] 📊 Timing breakdown: fanout={fanout_time_ms}ms, "
               f"heuristics={heuristic_time_ms}ms, judge={judge_time_ms}ms, "
               f"consensus={consensus_time_ms}ms, citations={citation_time_ms}ms")
    logger.info(f"[{trace_id}] 🏆 Winner: {winner_candidate.model} "
               f"({len(winner_candidate.text)} chars, confidence={confidence:.3f})")
    
    # Update model performance with final confidence
    judge_metrics.record_model_performance(
        winner_candidate.model,
        winner_candidate.gen_time_ms,
        confidence
    )
    
    return response_data

async def judge_health_check() -> Dict[str, Any]:
    """
    Get health information for the judge pipeline
    """
    health_info = {
        "pipeline_name": "judge",
        "step_performance": {},
        "model_performance": {},
        "recent_activity": {}
    }
    
    # Get step performance stats
    for step_name in ["fanout", "heuristics", "judge_scoring", "consensus", "citations", "total_pipeline"]:
        health_info["step_performance"][step_name] = judge_metrics.get_step_stats(step_name)
    
    # Get model performance summary
    for model, performances in judge_metrics.model_performance.items():
        if performances:
            recent_perfs = performances[-5:]  # Last 5 performances
            avg_time = sum(p["response_time_ms"] for p in recent_perfs) / len(recent_perfs)
            avg_confidence = sum(p["confidence"] for p in recent_perfs) / len(recent_perfs)
            
            health_info["model_performance"][model] = {
                "avg_response_time_ms": avg_time,
                "avg_confidence": avg_confidence,
                "recent_count": len(recent_perfs),
                "total_count": len(performances)
            }
    
    # Recent activity summary
    recent_candidates = list(judge_metrics.candidate_counts.items())[-10:]  # Last 10
    if recent_candidates:
        total_attempted = sum(data["attempted"] for _, data in recent_candidates)
        total_succeeded = sum(data["succeeded"] for _, data in recent_candidates)
        
        health_info["recent_activity"] = {
            "requests": len(recent_candidates),
            "total_models_attempted": total_attempted,
            "total_models_succeeded": total_succeeded,
            "success_rate": total_succeeded / total_attempted if total_attempted > 0 else 0
        }
    
    return health_info

async def optimize_judge_pipeline(trace_id: str = "optimize") -> Dict[str, Any]:
    """
    Analyze pipeline performance and suggest optimizations
    """
    logger.info(f"[{trace_id}] 🔧 Analyzing judge pipeline for optimizations...")
    
    health_info = await judge_health_check()
    optimizations = []
    
    # Analyze step performance
    step_perf = health_info.get("step_performance", {})
    
    # Check for slow steps
    if "total_pipeline" in step_perf:
        total_avg = step_perf["total_pipeline"].get("avg_ms", 0)
        if total_avg > 15000:  # > 15 seconds
            optimizations.append("Consider reducing model timeout or using fewer models")
    
    if "fanout" in step_perf:
        fanout_avg = step_perf["fanout"].get("avg_ms", 0)
        if fanout_avg > 10000:  # > 10 seconds
            optimizations.append("Fanout is slow - consider circuit breaker tuning or faster models")
    
    # Analyze model performance
    model_perf = health_info.get("model_performance", {})
    slow_models = []
    low_confidence_models = []
    
    for model, stats in model_perf.items():
        if stats.get("avg_response_time_ms", 0) > 8000:  # > 8 seconds
            slow_models.append(model)
        if stats.get("avg_confidence", 0) < 0.6:  # < 60% confidence
            low_confidence_models.append(model)
    
    if slow_models:
        optimizations.append(f"Consider removing slow models: {slow_models}")
    
    if low_confidence_models:
        optimizations.append(f"Low confidence models may need tuning: {low_confidence_models}")
    
    # Check success rates
    recent_activity = health_info.get("recent_activity", {})
    success_rate = recent_activity.get("success_rate", 0)
    
    if success_rate < 0.8:  # < 80% success rate
        optimizations.append("Low model success rate - check circuit breaker settings")
    
    return {
        "timestamp": time.time(),
        "health_summary": health_info,
        "optimizations": optimizations,
        "status": "healthy" if not optimizations else "needs_optimization"
    }