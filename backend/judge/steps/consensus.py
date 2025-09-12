# backend/judge/steps/consensus.py
from typing import Dict, Tuple


def _avg(d: Dict[str, float]) -> float:
    """
    Calculate average of trait scores with defensive clamping.
    """
    if not d:
        return 0.0
    # clamp defensively and average
    vals = [max(0.0, min(1.0, float(v))) for v in d.values()]
    return sum(vals) / len(vals)


def ensemble_consensus(judge_scores: Dict[int, Dict[str, float]]) -> Tuple[int, float]:
    """
    Combine per-candidate trait scores into a single score and pick a winner.

    Args:
        judge_scores: Dict mapping candidate index to trait scores
                     {0: {"accuracy": 0.8, "relevance": 0.9}, 1: {...}, ...}

    Returns:
        Tuple of (winner_idx, winner_avg_score)
        - winner_idx: Index of the winning candidate
        - winner_avg: Average score across all traits for the winner

    Notes:
        - Uses simple mean over traits (already normalized to 0..1)
        - Deterministic tie-break: lowest candidate index wins (stable)
        - Returns (-1, 0.0) if no scores provided
    """
    if not judge_scores:
        return -1, 0.0

    best_idx, best_avg = -1, -1.0

    for idx, trait_scores in judge_scores.items():
        avg = _avg(trait_scores)
        # Strictly greater picks a new winner; equal keeps earlier (deterministic)
        if avg > best_avg:
            best_idx, best_avg = idx, avg

    return best_idx, best_avg
