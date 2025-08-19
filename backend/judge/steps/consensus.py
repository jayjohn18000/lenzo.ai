# backend/judge/steps/llm_as_judge.py
"""
LLM-as-Judge scoring implementation
"""

import json
import logging
from typing import List, Dict, Any
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

def _build_rubric(req: RouteRequest) -> Dict[str, float]:
    """Build scoring rubric from request traits and options"""
    rubric = {}
    
    # Default traits
    default_traits = {
        "accuracy": 1.0,
        "clarity": 0.8,
        "completeness": 0.7,
        "relevance": 1.0
    }
    
    # Add custom rubric if provided
    if req.options and req.options.rubric:
        rubric.update(req.options.rubric)
    else:
        rubric.update(default_traits)
    
    # Add traits from expected_traits
    if req.expected_traits:
        for trait in req.expected_traits:
            if trait not in rubric:
                rubric[trait.lower()] = 0.8
    
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

{response_text}

Score this response on the following traits: {traits_list}

Return only JSON with scores 0.0-1.0."""
    
    try:
        judge_response, _ = await llm_complete(
            model=judge_model, 
            prompt=user_prompt, 
            system=system_prompt
        )
        
        # Parse JSON response
        cleaned_response = _clean_json_response(judge_response)
        scores = json.loads(cleaned_response)
        
        # Ensure all rubric traits are present and valid
        result = {}
        for trait in rubric:
            if trait in scores:
                try:
                    score = float(scores[trait])
                    result[trait] = max(0.0, min(1.0, score))  # Clamp to 0-1
                except (ValueError, TypeError):
                    result[trait] = 0.5  # neutral fallback
            else:
                result[trait] = 0.5  # missing trait fallback
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"[{trace_id}] Failed to parse judge response as JSON: {e}")
        return {trait: 0.5 for trait in rubric}
    except Exception as e:
        logger.error(f"[{trace_id}] Error in llm_judge: {e}")
        return {trait: 0.5 for trait in rubric}

def _clean_json_response(text: str) -> str:
    """Clean up JSON response from LLM to make it parseable"""
    cleaned = text.strip()
    
    # Remove code block markers
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    return cleaned.strip()