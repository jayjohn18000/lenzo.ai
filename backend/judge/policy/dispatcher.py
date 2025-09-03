# backend/judge/policy/dispatcher.py
import logging
from typing import Tuple, Set, Optional
from backend.judge.schemas import RouteRequest, PipelineID
from backend.judge.config import settings

logger = logging.getLogger(__name__)
# Traits that should force verifiable, source-backed output
FORCE_TOOL_TRAITS: Set[str] = {
    "non-hallucinated",
    "current",
    "accurate",
    "sources",
    "citations",
    "evidence",
    "verifiable",
}

# Categories that are typically high-risk or require verification
TOOL_CATEGORIES: Set[str] = {
    "science",
    "tech support",
    "finance",
    "legal",
    "medical",
}


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _normalize_traits(req: RouteRequest) -> Set[str]:
    traits = set(t.strip().lower() for t in (req.expected_traits or []))
    # also consider rubric keys as implicit traits
    if req.options and req.options.rubric:
        traits |= {str(k).strip().lower() for k in req.options.rubric.keys()}
    return traits


def decide_pipeline(req: RouteRequest) -> Tuple[PipelineID, str]:
    """
    First-stage decision (static): choose pipeline based on explicit override,
    traits, category, and citation requirements. The adaptive re-route based on
    judge confidence (< settings.CONF_THRESHOLD) happens later in execution.
    """
    # 1) Explicit override always wins
    if req.pipeline_id:
        return req.pipeline_id, "explicit-pipeline-id"

    traits = _normalize_traits(req)
    category = _norm(req.category)

    # 2) If traits/categories imply verification, choose tool_chain up front
    if traits & FORCE_TOOL_TRAITS:
        return "tool_chain", "trait-forced"
    if category in TOOL_CATEGORIES:
        return "tool_chain", "category-forced"

    # 3) Citations policy: we keep citations on for both pipelines.
    #    Requiring citations alone does not force tool_chain, but you can toggle here if desired.
    if req.options and req.options.require_citations:
        # keep judge as default; tool_chain is for when we must *verify* claims
        pass

    # 4) Default to judge (fast path). Adaptive escalation can happen later.
    return "judge", "default-judge"


def should_escalate_after_prepass(
    judge_confidence: Optional[float],
    req: RouteRequest,
) -> bool:
    if judge_confidence is None:
        return False
    
    # ADD THIS DEBUG LOG
    logger.info(f"Escalation check: confidence={judge_confidence}, threshold={settings.CONF_THRESHOLD}, will_escalate={judge_confidence < settings.CONF_THRESHOLD}")
    
    if judge_confidence < settings.CONF_THRESHOLD:
        return True
    return False
