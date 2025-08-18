# backend/judge/steps/rank_select.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any
from backend.judge.schemas import Candidate


def _weighted_score(
    scores: Dict[str, float] | None,
    weights: Dict[str, float] | None,
) -> float:
    """
    Compute a weighted score in [0,1] from a trait->score dict and weights.
    Falls back to simple average if weights are missing.
    """
    if not scores:
        return 0.0

    # Clamp and coerce just in case
    s = {k: max(0.0, min(1.0, float(v))) for k, v in scores.items()}

    if weights:
        # normalize weights so sum to 1 (ignore unknown traits)
        w = {k: float(weights.get(k, 0.0)) for k in s.keys()}
        total = sum(w.values())
        if total > 0:
            return sum(s[k] * (w[k] / total) for k in s.keys())
        # fall through to unweighted if weights sum to 0

    # simple average
    return sum(s.values()) / len(s)


def _extract_score(
    item: Dict[str, Any],
    weights: Dict[str, float] | None,
) -> float:
    """
    Be permissive about candidate schemas:
      - if item has top-level 'score' (numeric), use it
      - else if item['scores'] is a dict, compute weighted score
      - else 0.0
    """
    if isinstance(item.get("score"), (int, float)):
        return float(item["score"])

    scores = item.get("scores") or item.get("trait_scores") or None
    if isinstance(scores, dict):
        return _weighted_score(scores, weights)

    return 0.0


def rank_and_select(
    candidates: List[Any],
    judge_scores: Dict[int, Dict[str, float]],
    winner_info: Tuple[int, float],
    weights: Dict[str, float] | None = None,
) -> Tuple[Any, Dict[str, float], float]:
    """
    Judge pipeline version: select winner based on consensus results.
    Returns: (winner_candidate, scores_by_trait, confidence)
    """
    winner_idx, avg_score = winner_info
    
    if winner_idx < 0 or winner_idx >= len(candidates):
        # Fallback to first candidate if winner_idx is invalid
        winner_idx = 0
        avg_score = 0.5
    
    winner_cand = candidates[winner_idx]
    scores_by_trait = judge_scores.get(winner_idx, {})
    confidence = avg_score  # Use the consensus average as confidence
    
    return winner_cand, scores_by_trait, confidence


def best_by_verification(
    candidates: List[Candidate], 
    verifications: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]], float]:
    """
    Tool-chain pipeline version: select best candidate by verification coverage.
    Returns: (answer_text, evidence_list, confidence)
    """
    if not candidates or not verifications:
        return "No answer available", [], 0.0
    
    best_idx = 0
    best_score = 0.0
    
    # Find candidate with highest verified ratio
    for i, verification in enumerate(verifications):
        if i < len(candidates):
            stats = verification.get("stats", {})
            verified_ratio = stats.get("verified_ratio", 0.0)
            coverage_ratio = stats.get("coverage_ratio", 0.0)
            
            # Combine verified ratio and coverage ratio for scoring
            score = (verified_ratio * 0.7) + (coverage_ratio * 0.3)
            
            if score > best_score:
                best_score = score
                best_idx = i
    
    winner = candidates[best_idx]
    evidence = verifications[best_idx].get("evidence", [])
    confidence = best_score
    
    return winner.text, evidence, confidence


# ---- Back-compat alias ----
select_top = rank_and_select

__all__ = ["rank_and_select", "select_top", "best_by_verification"]