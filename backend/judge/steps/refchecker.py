# backend/judge/steps/refchecker.py
"""
RefChecker (MVP):
- Extract sentence-level claims.
- Prioritize by HDM-2 risk (high -> medium -> low).
- Heuristic verification:
    * If the sentence contains URLs or [n]-style citations → Verified (with sources).
    * If it contains numbers/years/temporal words but no sources → Failed (riskier factuals).
    * Otherwise → Weak (unverified but low-risk language).
- Outputs per-claim evidence and simple coverage metrics.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple, Any
from backend.judge.schemas import Candidate

URL_RE = re.compile(r'https?://[^\s\)\]]+')
BRACKET_CITE_RE = re.compile(r'\[(\d+)\]')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
NUMBER_RE = re.compile(r'\b\d[\d,]*(\.\d+)?\b')
TEMPORAL_RE = re.compile(
    r'\b(today|yesterday|recent(ly)?|last\s+(year|month|week)|this\s+(year|month|week)|'
    r'january|february|march|april|may|june|july|august|september|october|november|december)\b',
    re.IGNORECASE
)

# Safety: don't create too many claims on verbose answers
MAX_CLAIMS = 24


def _extract_sentences(text: str) -> List[Tuple[str, int, int]]:
    """Return [(sentence, start, end)] with simple split; preserves offsets."""
    # naive split on ., !, ? while keeping positions
    parts: List[str] = re.split(r'(?<=[\.\!\?])\s+', text.strip())
    out: List[Tuple[str, int, int]] = []
    cursor = 0
    for p in parts:
        s = p.strip()
        if not s:
            continue
        start = text.find(s, cursor)
        end = start + len(s)
        cursor = end
        out.append((s, start, end))
    return out


def _collect_sources(s: str) -> List[Dict[str, Any]]:
    """Extract sources as URIs with minimal metadata."""
    sources: List[Dict[str, Any]] = []
    for m in URL_RE.findall(s):
        sources.append({"type": "web", "uri": m, "snippet": s[:240]})
    for m in BRACKET_CITE_RE.findall(s):
        # Allow downstream to resolve bracketed references if present
        sources.append({"type": "ref", "id": m, "uri": f"ref:{m}", "snippet": s[:240]})
    return sources


def _verify_sentence(s: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Heuristic verifier:
    - URLs or bracket cites -> Verified
    - Numbers/years/temporal without sources -> Failed (needs evidence)
    - Else -> Weak
    """
    sources = _collect_sources(s)
    has_sources = len(sources) > 0
    has_year = bool(YEAR_RE.search(s))
    has_num = bool(NUMBER_RE.search(s))
    has_temp = bool(TEMPORAL_RE.search(s))

    if has_sources:
        return "Verified", sources
    if (has_year or has_num or has_temp):
        return "Failed", sources  # no sources, but factual-looking
    return "Weak", sources


def _sort_by_risk(sentences: List[Tuple[str, int, int]], risks: Dict) -> List[Tuple[str, int, int]]:
    """
    Use HDM-2 output to prioritize high->medium->low risk spans when truncating to MAX_CLAIMS.
    If risks is empty, preserve original order.
    """
    if not risks or not risks.get("risk_spans"):
        return sentences[:MAX_CLAIMS]

    # Build an index from offset to risk label
    span_risks = risks["risk_spans"]
    def risk_label_for(start: int, end: int) -> str:
        # Find overlapping risk span (first match wins)
        for rs in span_risks:
            if not isinstance(rs, dict):
                continue
            s0, e0 = int(rs.get("start", -1)), int(rs.get("end", -1))
            if s0 <= start <= e0 or s0 <= end <= e0 or (start <= s0 and end >= e0):
                return str(rs.get("risk", "low")).lower()
        return "low"

    priority = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(
        sentences,
        key=lambda x: (priority.get(risk_label_for(x[1], x[2]), 2), x[1])
    )
    return ranked[:MAX_CLAIMS]


async def verify_claims(candidate: Candidate, risks: Dict, trace_id: str) -> Dict[str, Any]:
    """
    Verify a candidate's claims using heuristics and (later) web/KB adapters.
    Returns:
      {
        "evidence": [
          { "claim_id": "c1", "text": "...", "status": "Verified|Weak|Failed|NotChecked",
            "sources": [{...}] },
          ...
        ],
        "stats": {
          "total": N, "verified": v, "weak": w, "failed": f,
          "verified_ratio": v/max(N,1),
          "coverage_ratio": (v+w+f)/max(N,1)
        }
      }
    """
    text = candidate.text or ""
    sents = _extract_sentences(text)
    prioritized = _sort_by_risk(sents, risks)

    evidence: List[Dict[str, Any]] = []
    v = w = f = 0
    for i, (s, start, end) in enumerate(prioritized, 1):
        status, sources = _verify_sentence(s)
        if status == "Verified":
            v += 1
        elif status == "Weak":
            w += 1
        elif status == "Failed":
            f += 1

        evidence.append({
            "claim_id": f"c{i}",
            "text": s,
            "status": status,
            "sources": sources,
            "notes": None
        })

    total = len(prioritized)
    stats = {
        "total": total,
        "verified": v,
        "weak": w,
        "failed": f,
        "verified_ratio": (v / total) if total else 0.0,
        "coverage_ratio": ((v + w + f) / total) if total else 0.0,
    }

    return {"evidence": evidence, "stats": stats}
