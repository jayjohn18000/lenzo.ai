# backend/judge/steps/fanout.py
import asyncio
import time
import logging
import random
from typing import List, Optional
from datetime import datetime
from backend.judge.schemas import Candidate
from backend.judge.clients.openrouter import llm_complete, OpenRouterError
from backend.judge.config import settings

logger = logging.getLogger(__name__)

def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for m in items:
        if m not in seen:
            out.append(m)
            seen.add(m)
    return out


def _select_optimal_models(
    requested_models: Optional[List[str]], 
    mode: str = "balanced"
) -> List[str]:
    """
    Select optimal models based on test results and mode
    """
    if requested_models:
        return requested_models
    
    if mode == "speed":
        return settings.SPEED_OPTIMIZED_MODELS[:settings.MAX_PARALLEL_FANOUT]
    elif mode == "quality":
        return settings.QUALITY_OPTIMIZED_MODELS[:settings.MAX_PARALLEL_FANOUT]
    elif mode == "cost":
        return settings.COST_OPTIMIZED_MODELS[:settings.MAX_PARALLEL_FANOUT]
    else:  # balanced
        models = settings.DEFAULT_MODELS[:settings.MAX_PARALLEL_FANOUT]
        
        # Add model rotation if enabled
        if settings.ENABLE_MODEL_ROTATION and len(settings.DEFAULT_MODELS) > settings.MAX_PARALLEL_FANOUT:
            # Randomly select from available models to distribute load
            all_models = settings.DEFAULT_MODELS + settings.FALLBACK_MODELS
            models = random.sample(all_models, min(settings.MAX_PARALLEL_FANOUT, len(all_models)))
        
        return models


async def _gen_one_with_fallback(
    model: str, 
    prompt: str, 
    sem: asyncio.Semaphore,
    fallback_models: List[str]
) -> Optional[Candidate]:
    """Generate with automatic fallback to backup models"""
    models_to_try = [model] + fallback_models
    
    for attempt_model in models_to_try:
        async with sem:
            t0 = time.perf_counter()
            try:
                logger.info(f"Attempting generation with model: {attempt_model}")
                text, meta = await llm_complete(model=attempt_model, prompt=prompt)
                dt_ms = int((time.perf_counter() - t0) * 1000)
                
                logger.info(f"✅ Success with {attempt_model}: {len(text)} chars in {dt_ms}ms")
                
                return Candidate(
                    text=text,
                    provider="openrouter",
                    model=attempt_model,  # Record actual model used
                    tokens_in=meta.get("tokens_in", 0),
                    tokens_out=meta.get("tokens_out", 0),
                    gen_time_ms=dt_ms,
                )
            except OpenRouterError as e:
                logger.warning(f"❌ Model {attempt_model} failed: {e}")
                if attempt_model == models_to_try[-1]:  # Last attempt
                    logger.error(f"All fallbacks exhausted for original model {model}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error for model {attempt_model}: {e}")
                continue
    
    return None


async def fanout_generate(
    prompt: str, 
    models: Optional[List[str]], 
    trace_id: str,
    mode: str = "balanced"
) -> List[Candidate]:
    """
    Generate candidate answers with smart model selection and fallbacks.
    
    Args:
        prompt: The user prompt
        models: Optional explicit model list
        trace_id: Trace ID for logging
        mode: Selection mode - "balanced", "speed", "quality", or "cost"
    """
    logger.info(f"🚀 Starting fanout generation for trace {trace_id}")
    logger.info(f"Mode: {mode}, Requested models: {models}")
    
    # Select optimal models based on your test results
    selected_models = _select_optimal_models(models, mode)
    
    if not selected_models:
        logger.error("No models available for fanout generation")
        return []
    
    selected_models = _dedupe_preserve_order(selected_models)
    logger.info(f"🎯 Selected models: {selected_models}")
    
    # Prepare fallback models for each primary model
    fallback_models = [m for m in settings.FALLBACK_MODELS if m not in selected_models][:2]
    
    sem = asyncio.Semaphore(max(1, settings.MAX_PARALLEL_FANOUT))
    
    # Create tasks with fallback support
    tasks = [
        asyncio.create_task(
            _gen_one_with_fallback(model, prompt, sem, fallback_models)
        ) 
        for model in selected_models
    ]
    
    logger.info(f"📡 Created {len(tasks)} generation tasks with fallbacks")
    
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    # Filter successful candidates
    candidates: List[Candidate] = []
    for i, result in enumerate(results):
        if isinstance(result, Candidate):
            candidates.append(result)
            logger.info(f"✅ Candidate {i}: {result.model} -> {len(result.text)} chars in {result.gen_time_ms}ms")
        else:
            logger.warning(f"❌ Failed candidate {i}: {selected_models[i] if i < len(selected_models) else 'unknown'}")
    
    # Log performance stats
    if candidates:
        avg_time = sum(c.gen_time_ms for c in candidates) / len(candidates)
        total_tokens = sum(c.tokens_in + c.tokens_out for c in candidates)
        logger.info(f"📊 Performance: {len(candidates)} candidates, avg {avg_time:.0f}ms, {total_tokens} total tokens")
    
    logger.info(f"🎉 Returning {len(candidates)} successful candidates")
    return candidates

def log_generation_event(trace_id, prompt, model, status, latency_ms, input_tokens, output_tokens, char_count):
    log_entry = {
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": prompt,
        "model": model,
        "status": status,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "char_count": char_count,
    }
    logger.info(f"[GENERATION_LOG] {log_entry}")