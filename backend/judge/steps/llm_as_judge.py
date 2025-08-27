# backend/judge/steps/llm_as_judge.py
"""
LLM-as-Judge scoring implementation with robust error handling
"""

import json
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.judge.schemas import Candidate, RouteRequest
from backend.judge.clients.openrouter import llm_complete
from backend.judge.config import settings

logger = logging.getLogger(__name__)

async def judge_candidates(
    candidates: List[Candidate], 
    req: RouteRequest, 
    trace_id: str
) -> Dict[int, Dict[str, float]]:
    """
    Score each candidate using LLM-as-Judge approach
    Returns: Dict[candidate_index] -> Dict[trait] -> score
    """
    if not candidates:
        return {}
    
    # Build rubric from request
    rubric = _build_rubric(req)
    judge_model = settings.JUDGE_MODEL
    
    logger.info(f"[{trace_id}] Judging {len(candidates)} candidates with {judge_model}")
    
    # NEW: Batch judging for performance
    if len(candidates) > 3 and settings.ENABLE_BATCH_JUDGING:
        return await _batch_judge_candidates(candidates, rubric, judge_model, trace_id)
    
    # Original sequential judging for small batches
    scores = {}
    for idx, candidate in enumerate(candidates):
        try:
            candidate_scores = await _judge_single_candidate(
                candidate.text, rubric, judge_model, trace_id
            )
            scores[idx] = candidate_scores
        except Exception as e:
            logger.warning(f"[{trace_id}] Failed to judge candidate {idx}: {e}")
            # Fallback to neutral scores
            scores[idx] = {trait: 0.5 for trait in rubric}
    
    return scores


async def _batch_judge_candidates(
    candidates: List[Candidate],
    rubric: Dict[str, float],
    judge_model: str,
    trace_id: str
) -> Dict[int, Dict[str, float]]:
    """
    Judge all candidates in a single batch for better performance
    """
    logger.info(f"[{trace_id}] Batch judging {len(candidates)} candidates")
    
    batch_prompt = _create_batch_prompt(candidates, rubric)
    
    try:
        response, _ = await llm_complete(
            model=judge_model,
            prompt=batch_prompt,
            system=BATCH_JUDGE_SYSTEM,
            temperature=0.1  # Low temperature for consistency
        )
        
        # Parse batch response
        scores = _parse_batch_scores(response, len(candidates), rubric)
        return scores
        
    except Exception as e:
        logger.error(f"[{trace_id}] Batch judging failed: {e}")
        # Fallback to sequential judging
        return await _fallback_sequential_judge(candidates, rubric, judge_model, trace_id)


def _create_batch_prompt(candidates: List[Candidate], rubric: Dict[str, float]) -> str:
    """Create a single prompt to judge all candidates"""
    traits_list = ", ".join(rubric.keys())
    
    prompt = f"Evaluate these {len(candidates)} responses on: {traits_list}\n\n"
    
    for i, candidate in enumerate(candidates):
        prompt += f"=== RESPONSE {i} (Model: {candidate.model}) ===\n"
        prompt += f"{candidate.text[:500]}...\n\n" if len(candidate.text) > 500 else f"{candidate.text}\n\n"
    
    prompt += f"""Return a JSON object with scores for each response:
{{
  "0": {{"accuracy": 0.85, "clarity": 0.90, ...}},
  "1": {{"accuracy": 0.75, "clarity": 0.95, ...}},
  ...
}}"""
    
    return prompt


def _parse_batch_scores(
    response: str, 
    num_candidates: int, 
    rubric: Dict[str, float]
) -> Dict[int, Dict[str, float]]:
    """Parse batch scoring response with robust error handling"""
    
    # Try to extract JSON from response
    json_match = re.search(r'\{[\s\S]*\}', response)
    if not json_match:
        raise ValueError("No JSON found in response")
    
    try:
        scores_dict = json.loads(json_match.group())
    except json.JSONDecodeError:
        # Try to fix common JSON errors
        cleaned = _clean_json_response(json_match.group())
        scores_dict = json.loads(cleaned)
    
    # Validate and normalize scores
    parsed_scores = {}
    for i in range(num_candidates):
        idx_key = str(i)
        if idx_key in scores_dict:
            parsed_scores[i] = _validate_scores(scores_dict[idx_key], rubric)
        else:
            # Missing candidate - use neutral scores
            parsed_scores[i] = {trait: 0.5 for trait in rubric}
    
    return parsed_scores


def _clean_json_response(json_str: str) -> str:
    """Clean common JSON formatting issues from LLM responses"""
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix single quotes
    json_str = json_str.replace("'", '"')
    
    # Remove comments
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    
    # Remove any text after the last }
    json_str = re.sub(r'}[^}]*$', '}', json_str)
    
    return json_str.strip()


def _validate_scores(scores: Dict, rubric: Dict[str, float]) -> Dict[str, float]:
    """Validate and normalize scores"""
    validated = {}
    
    for trait in rubric:
        if trait in scores:
            try:
                # Ensure score is float between 0 and 1
                score = float(scores[trait])
                validated[trait] = max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                validated[trait] = 0.5  # Neutral fallback
        else:
            validated[trait] = 0.5  # Missing trait
    
    return validated


def _build_rubric(req: RouteRequest) -> Dict[str, float]:
    """Build scoring rubric from request traits and options"""
    rubric = {}
    
    # Default traits with clearer descriptions
    default_traits = {
        "accuracy": 1.0,      # Factual correctness
        "clarity": 0.8,       # Clear and understandable
        "completeness": 0.7,  # Addresses all aspects
        "relevance": 1.0      # On-topic and focused
    }
    
    # Add custom rubric if provided
    if req.options and req.options.rubric:
        rubric.update(req.options.rubric)
    else:
        rubric.update(default_traits)
    
    # Add traits from expected_traits
    if req.expected_traits:
        for trait in req.expected_traits:
            normalized_trait = trait.lower().replace("-", "_").replace(" ", "_")
            if normalized_trait not in rubric:
                rubric[normalized_trait] = 0.8
    
    return rubric


async def _judge_single_candidate(
    response_text: str,
    rubric: Dict[str, float],
    judge_model: str,
    trace_id: str
) -> Dict[str, float]:
    """
    Judge a single candidate response against the rubric.
    Returns: Dict[trait_name, score] where score is 0.0-1.0
    """
    traits_list = ", ".join(rubric.keys())
    
    system_prompt = f"""You are an expert evaluator. Score the following response on these traits: {traits_list}

Scoring scale: 0.0 (poor) to 1.0 (excellent)

Return ONLY a JSON object with scores. Example: {{"accuracy": 0.85, "clarity": 0.92}}
Do not include any other text or explanation."""

    user_prompt = f"""Response to evaluate:

{response_text[:1000]}{'...' if len(response_text) > 1000 else ''}

Score this response on the following traits: {traits_list}

Return only JSON with scores 0.0-1.0."""

    try:
        result, _ = await llm_complete(
            model=judge_model,
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.1,
            max_tokens=200
        )
        
        # Robust JSON parsing
        return _parse_single_score(result, rubric)
        
    except Exception as e:
        logger.error(f"[{trace_id}] Judge scoring failed: {e}")
        raise


def _parse_single_score(response: str, rubric: Dict[str, float]) -> Dict[str, float]:
    """Parse single candidate score with error handling"""
    
    # Try direct JSON parsing first
    try:
        # Look for JSON in the response
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            scores = json.loads(json_match.group())
            return _validate_scores(scores, rubric)
    except json.JSONDecodeError:
        pass
    
    # Fallback: Try to extract scores using regex
    scores = {}
    for trait in rubric:
        # Look for patterns like "accuracy: 0.85" or "accuracy": 0.85
        pattern = rf'"{trait}"\s*:\s*(0?\.\d+|1\.0|0|1)'
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            scores[trait] = float(match.group(1))
    
    if scores:
        return _validate_scores(scores, rubric)
    
    # Last resort: look for any numbers
    numbers = re.findall(r'(0?\.\d+|1\.0)', response)
    if len(numbers) == len(rubric):
        # Assume they're in order
        return {trait: float(numbers[i]) for i, trait in enumerate(rubric)}
    
    raise ValueError(f"Could not parse scores from response: {response[:200]}...")


async def _fallback_sequential_judge(
    candidates: List[Candidate],
    rubric: Dict[str, float],
    judge_model: str,
    trace_id: str
) -> Dict[int, Dict[str, float]]:
    """Fallback to sequential judging if batch fails"""
    logger.warning(f"[{trace_id}] Falling back to sequential judging")
    
    scores = {}
    tasks = []
    
    # Create tasks for parallel execution
    for idx, candidate in enumerate(candidates):
        task = asyncio.create_task(
            _judge_with_retry(candidate.text, rubric, judge_model, trace_id, idx)
        )
        tasks.append(task)
    
    # Execute with some concurrency control
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"[{trace_id}] Judge task {idx} failed: {result}")
            scores[idx] = {trait: 0.5 for trait in rubric}
        else:
            scores[idx] = result
    
    return scores


async def _judge_with_retry(
    text: str,
    rubric: Dict[str, float],
    model: str,
    trace_id: str,
    idx: int,
    max_retries: int = 2
) -> Dict[str, float]:
    """Judge with retry logic"""
    for attempt in range(max_retries):
        try:
            return await _judge_single_candidate(text, rubric, model, trace_id)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"[{trace_id}] Retry {attempt+1} for candidate {idx}")
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff


# System prompts
BATCH_JUDGE_SYSTEM = """You are an expert evaluator scoring multiple AI responses.
Be consistent in your scoring across all responses.
Use the full range of scores (0.0 to 1.0) to differentiate quality.
Return valid JSON only."""