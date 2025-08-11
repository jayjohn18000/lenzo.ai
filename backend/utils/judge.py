# /utils/judge.py
import os
import asyncio
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv
from statistics import mean, pstdev
from backend.judging.adapters import parse_judge_output, normalize

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

async def score_responses(*, responses: List[Dict[str, Any]], judge_models: List[str], prompt: str) -> Dict[str, Any]:
    """
    responses: [{ "model": "...", "response": "..." }, ...]
    For each response, ask each judge model to evaluate. Mix numeric & vote-only.
    """
    # Pseudo-call to your LLM client pool
    results: Dict[str, Dict[str, Any]] = {r["model"]: {"judgments": []} for r in responses}

    for r in responses:
        for jm in judge_models:
            # call_judge_model must return raw text from the judge model
            raw = await call_judge_model(jm, prompt, r["response"])
            score01, label, reasons = parse_judge_output(raw)
            results[r["model"]]["judgments"].append({
                "judge_model": jm,
                "raw": raw,
                "score01": score01,      # can be None
                "label": label,
                "reasons": reasons
            })

    # aggregate per candidate
    for model, data in results.items():
        scores = [j["score01"] for j in data["judgments"] if j["score01"] is not None]
        votes  = [ (j.get("label") or "").lower() for j in data["judgments"] if j["score01"] is None ]

        agg = {}
        if scores:
            agg["score_mean"] = mean(scores)
            agg["score_stdev"] = pstdev(scores) if len(scores) > 1 else 0.0
        if votes:
            from collections import Counter
            counts = Counter(votes)
            top, n = (None,0)
            if counts:
                top, n = counts.most_common(1)[0]
            agg["vote_top_label"] = top
            agg["vote_top_count"] = n
            agg["vote_total"] = len(votes)

        data["aggregate"] = agg

    # pick winner: prefer numeric mean; fallback to votes; then to first non-empty
    def winner_key(item):
        model, data = item
        agg = data.get("aggregate", {})
        if "score_mean" in agg:
            return (1, agg["score_mean"])  # numeric wins
        elif "vote_top_count" in agg:
            # normalize vote fraction as proxy score
            frac = agg["vote_top_count"] / max(1, agg["vote_total"])
            return (0, frac)
        return (0, 0.0)

    ranked = sorted(results.items(), key=winner_key, reverse=True)
    best_model, best_data = ranked[0]
    best_score = best_data.get("aggregate", {}).get("score_mean")

    return {
        "ranking": [
            {
                "model": m,
                "aggregate": d.get("aggregate", {}),
                "judgments": d["judgments"]
            } for m, d in ranked
        ],
        "winner": {
            "model": best_model,
            "score": best_score
        }
    }

# stub: you’ll route to OpenAI/Anthropic/Gemini, etc.
async def call_judge_model(judge_model: str, prompt: str, candidate_answer: str) -> str:
    # TODO: implement using your existing LLM client(s)
    # Ensure you pass the JUDGE_SYSTEM + judge_prompt(...) to the correct provider
    return '{"score": 8.5, "label": "mostly_correct", "reasons": "example"}'
