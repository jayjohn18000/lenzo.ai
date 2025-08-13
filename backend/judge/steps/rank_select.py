# backend/judge/steps/rank_select.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any


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
    candidates: List[Dict[str, Any]],
    *,
    weights: Dict[str, float] | None = None,
    k: int = 1,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Rank candidates by (weighted) score and return top-k along with debug meta.
      candidates: list of dicts, expected keys:
        - 'text': str (candidate answer)  (optional but typical)
        - 'scores' or 'trait_scores': {trait: score in [0,1]} OR 'score': float
      weights: {trait: weight} (any scale; normalized internally)
      k: how many to return

    Returns: (winners, meta)
      winners: top-k list (each has an added 'final_score' field)
      meta: { 'k': int, 'weights_used': dict|None, 'ranking': [ (idx, score) ] }
    """
    if not candidates:
        return [], {"k": k, "weights_used": weights, "ranking": []}

    scored = []
    for idx, item in enumerate(candidates):
        s = _extract_score(item, weights)
        scored.append((idx, s))

    # sort high to low
    scored.sort(key=lambda tup: tup[1], reverse=True)

    winners: List[Dict[str, Any]] = []
    for idx, s in scored[: max(1, k)]:
        # copy to avoid mutating input
        chosen = dict(candidates[idx])
        chosen["final_score"] = s
        winners.append(chosen)

    meta = {
        "k": k,
        "weights_used": weights,
        "ranking": scored,  # list of (original_index, score)
    }
    return winners, meta

def best_by_verification(*args, **kwargs):
    """
    Placeholder for the original best_by_verification logic.
    Replace this with the actual implementation.
    """
    raise NotImplementedError("best_by_verification() is not yet implemented.")


# ---- Back-compat alias (if the pipeline imported the wrong name earlier) ----
select_top = rank_and_select

__all__ = ["rank_and_select", "select_top"]
