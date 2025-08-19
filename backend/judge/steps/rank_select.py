# backend/judge/steps/rank_select.py
"""
Final ranking and selection of the winning candidate
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from statistics import mean
from backend.judge.schemas import Candidate

logger = logging.getLogger(__name__)

def rank_and_select(
    candidates: List[Candidate],
    judge_scores: Dict[int, Dict[str, float]],
    consensus_result: Tuple[int, float]
) -> Tuple[Candidate, Dict[str, float], float]:
    """
    Final selection and confidence calculation
    Returns: (winner_candidate, scores_by_trait, confidence)
    """
    if not candidates:
        raise ValueError("No candidates provided")
    
    winner_idx, consensus_score = consensus_result
    
    if winner_idx >= len(candidates):
        raise ValueError(f"Winner index {winner_idx} out of range for {len(candidates)} candidates")
    
    winner_candidate = candidates[winner_idx]
    winner_trait_scores = judge_scores.get(winner_idx, {})
    
    # Calculate final confidence
    confidence = _calculate_final_confidence(
        winner_candidate, 
        winner_trait_scores, 
        consensus_score,
        candidates,
        judge_scores
    )
    
    logger.info(f"Selected winner: {winner_candidate.model} with confidence {confidence:.3f}")
    
    return winner_candidate, winner_trait_scores, confidence

def _calculate_final_confidence(
    winner: Candidate,
    winner_scores: Dict[str, float],
    consensus_score: float,
    all_candidates: List[Candidate],
    all_scores: Dict[int, Dict[str, float]]
) -> float:
    """
    Calculate final confidence based on multiple factors
    """
    confidence_factors = []
    
    # Base consensus score
    confidence_factors.append(consensus_score)
    
    # Winner margin (how much better than second place)
    if len(all_candidates) > 1:
        all_averages = []
        for idx, scores in all_scores.items():
            if scores:
                avg = mean(scores.values())
                all_averages.append(avg)
        
        if len(all_averages) >= 2:
            all_averages.sort(reverse=True)
            margin = all_averages[0] - all_averages[1]
            margin_confidence = min(1.0, margin * 2)  # Scale margin to confidence
            confidence_factors.append(margin_confidence)
    
    # Response quality indicators
    if winner.text:
        # Length quality
        text_length = len(winner.text)
        if 50 <= text_length <= 1000:
            length_confidence = 0.8
        elif text_length < 50:
            length_confidence = 0.4
        else:
            length_confidence = 0.6
        confidence_factors.append(length_confidence)
        
        # Heuristic score if available
        if winner.heuristic_score is not None:
            confidence_factors.append(winner.heuristic_score)
    
    # Model reliability factor
    model_reliability = _get_model_reliability(winner.model)
    confidence_factors.append(model_reliability)
    
    # Calculate weighted average
    final_confidence = mean(confidence_factors) if confidence_factors else 0.5
    
    return max(0.0, min(1.0, final_confidence))

def _get_model_reliability(model_name: str) -> float:
    """
    Get reliability score for different models based on known performance
    """
    # Model reliability mapping based on general performance
    reliability_map = {
        "openai/gpt-4o": 0.95,
        "openai/gpt-4o-mini": 0.90,
        "anthropic/claude-3.5-sonnet": 0.95,
        "anthropic/claude-3-opus": 0.92,
        "anthropic/claude-3-sonnet": 0.88,
        "anthropic/claude-3-haiku": 0.85,
        "google/gemini-pro-1.5": 0.87,
        "google/gemini-flash-1.5": 0.83,
        "meta-llama/llama-3.1-70b-instruct": 0.82,
        "mistralai/mistral-large": 0.85,
        "mistralai/mistral-medium": 0.80,
        "mistralai/mistral-small": 0.78,
    }
    
    # Extract base model name for matching
    base_model = model_name.lower()
    
    for model_pattern, reliability in reliability_map.items():
        if model_pattern.lower() in base_model:
            return reliability
    
    # Default reliability for unknown models
    return 0.75