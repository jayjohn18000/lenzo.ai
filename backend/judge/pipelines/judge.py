# backend/judge/pipelines/judge.py
from typing import Dict, Tuple
from backend.judge.schemas import RouteRequest, Candidate
from backend.judge.config import settings
from backend.judge.steps.fanout import fanout_generate
from backend.judge.steps.heuristics import score_heuristics
from backend.judge.steps.llm_as_judge import judge_candidates
from backend.judge.steps.consensus import ensemble_consensus
from backend.judge.steps.rank_select import rank_and_select
from backend.judge.utils.citations import extract_citations


async def run_judge(req: RouteRequest, trace_id: str) -> Dict:
    """
    Judge pipeline:
      1) Fan-out generation across models
      2) Heuristic pre-scores
      3) LLM-as-Judge scoring per candidate (trait-based)
      4) Consensus + selection
      5) Citations extraction (URLs) and normalized response
    """
    # 1) Fan-out → parallel generations
    models = req.options.models or settings.DEFAULT_MODELS
    candidates = await fanout_generate(req.prompt, models, trace_id)

    # guard: if nothing came back, fail early with a clear error
    if not candidates:
        raise RuntimeError("No candidates returned from fan-out generation")

    # 2) Heuristic features (refusals/length, etc.)
    candidates = score_heuristics(candidates)

    # 3) Judge per candidate against rubric/traits
    judge_scores = await judge_candidates(candidates, req, trace_id)  # Dict[idx] -> Dict[trait->score]

    # 4) Consensus + winner selection
    winner_idx, avg_score = ensemble_consensus(judge_scores)  # (index, avg across traits)
    winner_cand, scores_by_trait, confidence = rank_and_select(candidates, judge_scores, (winner_idx, avg_score))

    # 5) Citations (always on, may be empty)
    citations = extract_citations(winner_cand.text)

    return {
        "answer": winner_cand.text,
        "winner_model": winner_cand.model,
        "scores_by_trait": scores_by_trait,
        "confidence": confidence,          # used by runner for adaptive escalation (<0.85)
        "citations": citations,
    }
