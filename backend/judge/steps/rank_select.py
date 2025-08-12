# judge/rank_select.py

from typing import List, Dict, Any, Optional


def rank_responses(judged_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Rank candidate responses based on aggregated judge scores.
    Prefers numeric scores; falls back to vote-based results.
    """
    if not judged_responses:
        return {"ranking": [], "winner": None}

    # Sort by score_mean (numeric) if available, otherwise vote fraction
    def sort_key(item: Dict[str, Any]) -> tuple:
        agg = item.get("aggregate", {})
        if "score_mean" in agg:
            return (1, agg["score_mean"])
        elif "vote_top_count" in agg:
            frac = agg["vote_top_count"] / max(1, agg.get("vote_total", 1))
            return (0, frac)
        return (0, 0.0)

    ranked = sorted(judged_responses, key=sort_key, reverse=True)

    # Winner is first in sorted list
    winner = ranked[0] if ranked else None
    return {
        "ranking": ranked,
        "winner": winner
    }


def select_top_n(
    judged_responses: List[Dict[str, Any]], n: int = 1
) -> List[Dict[str, Any]]:
    """
    Select top-N responses from the ranked list.
    """
    ranked_data = rank_responses(judged_responses)["ranking"]
    return ranked_data[:n]


def select_above_threshold(
    judged_responses: List[Dict[str, Any]], threshold: float
) -> List[Dict[str, Any]]:
    """
    Select all responses above a given score_mean threshold.
    Falls back to vote fraction if no numeric score.
    """
    selected = []
    for item in judged_responses:
        agg = item.get("aggregate", {})
        if "score_mean" in agg:
            if agg["score_mean"] >= threshold:
                selected.append(item)
        elif "vote_top_count" in agg:
            frac = agg["vote_top_count"] / max(1, agg.get("vote_total", 1))
            if frac >= threshold:
                selected.append(item)
    return selected
