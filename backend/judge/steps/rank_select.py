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
    consensus_result: Tuple[int, float],
) -> Tuple[Candidate, Dict[str, float], float]:
    """
    Final selection and confidence calculation
    Returns: (winner_candidate, scores_by_trait, confidence)
    """
    if not candidates:
        raise ValueError("No candidates provided")

    winner_idx, consensus_score = consensus_result

    if winner_idx >= len(candidates):
        raise ValueError(
            f"Winner index {winner_idx} out of range for {len(candidates)} candidates"
        )

    winner_candidate = candidates[winner_idx]
    winner_trait_scores = judge_scores.get(winner_idx, {})

    # Calculate final confidence
    confidence = _calculate_final_confidence(
        winner_candidate, winner_trait_scores, consensus_score, candidates, judge_scores
    )

    logger.info(
        f"Selected winner: {winner_candidate.model} with confidence {confidence:.3f}"
    )

    return winner_candidate, winner_trait_scores, confidence


def _calculate_final_confidence(
    winner: Candidate,
    winner_scores: Dict[str, float],
    consensus_score: float,
    all_candidates: List[Candidate],
    all_scores: Dict[int, Dict[str, float]],
) -> float:
    """
    Calculate final confidence based on multiple factors.
    FIXED: Prioritize judge consensus score rather than diluting with other factors.
    """
    # Start with the consensus score as the primary confidence
    base_confidence = consensus_score

    # Apply modifiers instead of averaging everything equally
    confidence_modifiers = []

    # 1. Winner margin modifier (±10% max)
    if len(all_candidates) > 1:
        all_averages = []
        for idx, scores in all_scores.items():
            if scores:
                avg = mean(scores.values())
                all_averages.append(avg)

        if len(all_averages) >= 2:
            all_averages.sort(reverse=True)
            margin = all_averages[0] - all_averages[1]
            # If winner has significant margin, boost confidence slightly
            # If very close race, reduce confidence slightly
            if margin > 0.2:
                confidence_modifiers.append(0.1)  # +10% for clear winner
            elif margin < 0.05:
                confidence_modifiers.append(-0.1)  # -10% for very close race

    # 2. Response quality modifier (±5% max)
    if winner.text:
        text_length = len(winner.text)
        if 100 <= text_length <= 2000:
            confidence_modifiers.append(0.05)  # Good length
        elif text_length < 50:
            confidence_modifiers.append(-0.1)  # Too short
        elif text_length > 5000:
            confidence_modifiers.append(-0.05)  # Too verbose

    # 3. Model reliability modifier (±5% max)
    model_reliability = _get_model_reliability(winner.model)
    if model_reliability >= 0.9:
        confidence_modifiers.append(0.05)  # Premium model bonus
    elif model_reliability < 0.8:
        confidence_modifiers.append(-0.05)  # Lower tier model penalty

    # Apply modifiers to base confidence
    modifier_sum = sum(confidence_modifiers)
    final_confidence = base_confidence + modifier_sum

    # Log the calculation for debugging
    logger.debug(
        f"Confidence calculation: base={base_confidence:.3f}, modifiers={modifier_sum:.3f}, final={final_confidence:.3f}"
    )

    # Ensure bounds [0.0, 1.0]
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
