# backend/judge/steps/llm_as_judge.py
import asyncio
from typing import Dict, List

from backend.judge.schemas import Candidate, RouteRequest
from backend.judge.config import settings
from backend.judge.clients.openrouter import llm_judge


def _build_rubric(req: RouteRequest) -> Dict[str, float]:
    """
    Build a simple trait->weight rubric.
    Priority: explicit rubric in options > expected_traits (equal weights) > defaults.
    """
    if req.options and req.options.rubric:
        # ensure weights are floats in [0,1]
        r = {}
        for k, v in req.options.rubric.items():
            try:
                r[str(k)] = max(0.0, min(1.0, float(v)))
            except Exception:
                r[str(k)] = 1.0
        return r

    traits = req.expected_traits or ["accuracy", "clarity"]
    if not traits:
        traits = ["accuracy", "clarity"]
    weight = 1.0 / max(1, len(traits))
    return {t: weight for t in traits}


async def _score_one(idx: int, cand: Candidate, rubric: Dict[str, float]) -> Dict[str, float]:
    scores = await llm_judge(candidate=cand.text, rubric=rubric, judge_model=settings.JUDGE_MODEL)
    # Make sure all rubric traits exist in the output
    for t in rubric.keys():
        scores[t] = max(0.0, min(1.0, float(scores.get(t, 0.0))))
    return scores


async def judge_candidates(cands: List[Candidate], req: RouteRequest, trace_id: str) -> Dict[int, Dict[str, float]]:
    """
    Ask the judge model to score each candidate on rubric traits (0..1).
    Returns: {candidate_index: {trait: score}}
    """
    rubric = _build_rubric(req)
    tasks = [asyncio.create_task(_score_one(i, c, rubric)) for i, c in enumerate(cands)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    judged: Dict[int, Dict[str, float]] = {}
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            # fallback: neutral 0.5 for all traits on failure
            judged[i] = {t: 0.5 for t in rubric.keys()}
        else:
            judged[i] = res
    return judged
