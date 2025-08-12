# backend/judge/pipelines/tool_chain.py
from typing import Dict, List
from backend.judge.schemas import RouteRequest, Candidate
from backend.judge.steps.uqlm import generate_with_uqlm
from backend.judge.steps.hdm2 import detect_hallucinations
from backend.judge.steps.refchecker import verify_claims
from backend.judge.steps.rank_select import best_by_verification
from backend.judge.utils.citations import normalize_evidence_to_citations


async def run_tool_chain(req: RouteRequest, trace_id: str) -> Dict:
    """
    Tool-chain pipeline:
      1) UQLM generator (n>=1)
      2) HDM-2 hallucination detector (span-level risk tagging)
      3) RefChecker verification per claim (evidence collection)
      4) Pick best candidate by verified coverage; compute confidence
      5) Normalize citations from evidence (always on)
    """
    # 1) Generate one or more drafts (can wire tools/RAG later)
    gens: List[Candidate] = await generate_with_uqlm(req.prompt, trace_id, n=2)
    if not gens:
        raise RuntimeError("UQLM generator returned no drafts")

    # 2) Risk tagging per draft (sync stub for now)
    risks = [detect_hallucinations(g) for g in gens]

    # 3) Verify claims for each draft (async)
    verifications = []
    for g, r in zip(gens, risks):
        v = await verify_claims(g, r, trace_id)
        verifications.append(v)

    # 4) Pick best-by-verification and compute confidence
    answer, evidence_list, confidence = best_by_verification(gens, verifications)

    # 5) Normalize citations from evidence
    citations = normalize_evidence_to_citations(evidence_list)

    return {
        "answer": answer,
        "winner_model": "uqlm",  # placeholder until real model ids are plumbed through
        "evidence": evidence_list,
        "confidence": confidence,
        "citations": citations,
    }
