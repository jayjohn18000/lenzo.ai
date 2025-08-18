# backend/judge/pipelines/judge.py
from typing import Dict, List
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
    Judge pipeline with proper metrics tracking:
      1) Fan-out generation across models
      2) Heuristic pre-scores
      3) LLM-as-Judge scoring per candidate (trait-based)
      4) Consensus + selection
      5) Citations extraction (URLs) and normalized response
    """
    # 1) Fan-out → parallel generations
    models = req.options.models or settings.DEFAULT_MODELS
    mode = req.options.model_selection_mode
    candidates = await fanout_generate(req.prompt, models, trace_id, mode)

    # guard: if nothing came back, fail early with a clear error
    if not candidates:
        raise RuntimeError("No candidates returned from fan-out generation")

    # Track models attempted and succeeded
    models_attempted = list(set(c.model for c in candidates if c.model))
    models_succeeded = [c.model for c in candidates if c.text and len(c.text) > 0]

    # 2) Heuristic features (refusals/length, etc.)
    candidates = score_heuristics(candidates)

    # 3) Judge per candidate against rubric/traits
    judge_scores = await judge_candidates(candidates, req, trace_id)  # Dict[idx] -> Dict[trait->score]

    # 4) Consensus + winner selection
    winner_idx, avg_score = ensemble_consensus(judge_scores)  # (index, avg across traits)
    winner_cand, scores_by_trait, confidence = rank_and_select(candidates, judge_scores, (winner_idx, avg_score))

    # 5) Citations (always on, may be empty)
    citations = extract_citations(winner_cand.text)

    # Ensure scores_by_trait has proper float values
    if scores_by_trait:
        scores_by_trait = {k: float(v) for k, v in scores_by_trait.items()}

    return {
        "answer": winner_cand.text,
        "winner_model": winner_cand.model,
        "scores_by_trait": scores_by_trait,
        "confidence": float(confidence),
        "citations": citations,
        "models_attempted": models_attempted,
        "models_succeeded": models_succeeded,
    }