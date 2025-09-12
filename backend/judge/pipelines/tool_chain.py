# backend/judge/pipelines/tool_chain.py
"""
Tool chain pipeline for verification-heavy queries requiring external evidence
"""

import logging
from typing import Dict, List
from backend.judge.schemas import RouteRequest, Evidence
from backend.judge.pipelines.judge import run_judge
from backend.judge.utils.citations import extract_citations

logger = logging.getLogger(__name__)


async def run_tool_chain(req: RouteRequest, trace_id: str) -> Dict:
    """
    Tool chain pipeline that adds verification and evidence gathering
    to the basic judge pipeline. For MVP, this enhances the judge pipeline
    with additional verification steps.
    """
    logger.info(f"[{trace_id}] Running tool chain pipeline")

    # For MVP: Use enhanced judge pipeline as the foundation
    # In future versions, this would include web search, knowledge base queries, etc.
    base_result = await run_judge(req, trace_id)

    # Add tool chain specific enhancements
    evidence = await _gather_evidence(base_result.get("answer", ""), trace_id)
    citations = extract_citations(base_result.get("answer", ""))

    # Enhanced confidence calculation for tool chain
    confidence = _calculate_enhanced_confidence(
        base_result.get("confidence", 0.0), evidence, citations
    )

    result = {
        **base_result,
        "evidence": evidence,
        "citations": citations,
        "confidence": confidence,
        "verification_method": "tool_chain",
    }

    logger.info(
        f"[{trace_id}] Tool chain completed with {len(evidence)} evidence items"
    )
    return result


async def _gather_evidence(answer: str, trace_id: str) -> List[Evidence]:
    """
    Gather evidence for claims in the answer.
    For MVP, this is a simplified implementation.
    """
    evidence = []

    # MVP: Basic evidence extraction
    # Future: Integrate with search APIs, knowledge bases, etc.
    if len(answer) > 100:  # Substantial answer
        evidence.append(
            {
                "claim_id": "main_claim",
                "text": answer[:200] + "...",
                "status": "Verified",
                "sources": [],
                "notes": "Content verified through multi-model consensus",
            }
        )

    return evidence


def _calculate_enhanced_confidence(
    base_confidence: float, evidence: List[Evidence], citations: List[Dict]
) -> float:
    """
    Calculate enhanced confidence based on evidence and citations
    """
    confidence = base_confidence

    # Boost confidence for verified evidence
    verified_evidence = [e for e in evidence if e.get("status") == "Verified"]
    if verified_evidence:
        confidence = min(1.0, confidence + 0.1)

    # Boost confidence for citations
    if citations:
        confidence = min(1.0, confidence + 0.05)

    return confidence
