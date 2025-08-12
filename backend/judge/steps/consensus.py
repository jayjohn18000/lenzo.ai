# backend/judge/steps/consensus.py
from typing import Dict, Tuple

def _avg(d: Dict[str, float]) -> float:
    if not d:
        return 0.0
    # clamp defensively and average
    vals = [max(0.0, min(1.0, float(v))) for v in d.values()]
    return sum(vals) / len(vals)

def ensemble_consensus(judge_scores: Dict[int, Dict[str, float]]) -> Tuple[int, float]:
    """
    Combine per-candidate trait scores into a single score and pick a winner.
    - Uses simple mean over traits (already 0..1).
    - Deterministic tie-break: lowest candidate index wins (stable).
    Returns: (winner_idx, winner_avg)
    """
    if not judge_scores:
        return -1, 0.0

    best_idx, best_avg = -1, -1.0
    for idx, trait_scores in judge_scores.items():
        avg = _avg(trait_scores)
        # strictly greater picks a new winner; equal keeps earlier (deterministic)
        if avg > best_avg:
            best_idx, best_avg = idx, avg

    return best_idx, best_avg
