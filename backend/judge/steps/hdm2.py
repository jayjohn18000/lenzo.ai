# backend/judge/steps/hdm2.py
"""
HDM-2 (stub): Hallucination risk tagging at the span level.

Heuristics used (cheap + fast for MVP):
- Sentences with hard numbers but no citation markers → higher risk
- Temporal claims (years, 'recent', 'today', month names) → medium risk
- Hedging / speculative language ('probably', 'it seems', 'reportedly') → medium risk
- Very short or very long sentences get slight penalties
- Presence of URLs/citation markers lowers risk modestly

Return shape:
{
  "risk_spans": [
      {"span": "text...", "start": 0, "end": 42, "risk": "high", "reasons": ["number_no_cite"]},
      ...
  ],
  "summary": "N spans flagged (H/M/L), overall risk: 0.42",
  "overall_risk": 0.42
}
"""
import re
from typing import Dict, List, Tuple
from backend.judge.schemas import Candidate

SPLIT_SENT = re.compile(r"(?<=[\.\!\?])\s+")
HAS_URL = re.compile(r"https?://\S+")
HAS_BRACKET_CITE = re.compile(
    r"\[\d+\]|\([^)]+(?:source|ref|doi)[^)]+\)", re.IGNORECASE
)
HAS_YEAR = re.compile(r"\b(19|20)\d{2}\b")
HAS_NUMBER = re.compile(r"\b\d[\d,]*(\.\d+)?\b")
TEMPORAL_WORDS = re.compile(
    r"\b(today|yesterday|recent(ly)?|last\s+(year|month|week)|this\s+(year|month|week)|"
    r"january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)
HEDGES = re.compile(
    r"\b(might|may|could|likely|probably|apparently|reportedly|seems)\b", re.IGNORECASE
)


def _risk_for_sentence(s: str) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    risk = 0.0

    has_url = bool(HAS_URL.search(s)) or bool(HAS_BRACKET_CITE.search(s))
    has_year = bool(HAS_YEAR.search(s))
    has_num = bool(HAS_NUMBER.search(s))
    has_temp = bool(TEMPORAL_WORDS.search(s))
    has_hedge = bool(HEDGES.search(s))
    length = len(s)

    # Numbers without citations → push risk
    if has_num and not has_url:
        risk += 0.35
        reasons.append("number_no_cite")

    # Specific years / temporal words → add risk
    if has_year or has_temp:
        risk += 0.2
        reasons.append("temporal_claim")

    # Hedging words suggest uncertainty
    if has_hedge:
        risk += 0.15
        reasons.append("hedging_language")

    # Very short or very long sentences get slight penalties
    if length < 40:
        risk += 0.1
        reasons.append("too_short")
    elif length > 300:
        risk += 0.1
        reasons.append("too_long")

    # Presence of citations/URLs reduces risk a bit (but not below 0)
    if has_url:
        risk = max(0.0, risk - 0.15)
        reasons.append("has_citation")

    # Clamp
    risk = max(0.0, min(1.0, risk))
    return risk, reasons


def detect_hallucinations(candidate: Candidate) -> Dict:
    """
    Analyze candidate.text and tag risky spans. Output used to prioritize RefChecker.
    """
    text = candidate.text or ""
    if not text.strip():
        return {"risk_spans": [], "summary": "empty text", "overall_risk": 0.0}

    # Split into sentences while tracking offsets
    risk_spans: List[Dict] = []
    idx = 0
    sentences = SPLIT_SENT.split(text)
    cursor = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        start = text.find(s, cursor)
        end = start + len(s)
        cursor = end

        risk, reasons = _risk_for_sentence(s)
        label = "low"
        if risk >= 0.66:
            label = "high"
        elif risk >= 0.33:
            label = "medium"

        risk_spans.append(
            {
                "span": s,
                "start": start,
                "end": end,
                "risk": label,
                "score": round(risk, 3),
                "reasons": reasons,
            }
        )
        idx += 1

    # Overall risk = mean of per-sentence scores (simple MVP)
    if risk_spans:
        overall = sum(rs["score"] for rs in risk_spans) / len(risk_spans)
    else:
        overall = 0.0

    high = sum(1 for rs in risk_spans if rs["risk"] == "high")
    med = sum(1 for rs in risk_spans if rs["risk"] == "medium")
    low = sum(1 for rs in risk_spans if rs["risk"] == "low")
    summary = f"{len(risk_spans)} spans flagged (H:{high}/M:{med}/L:{low}), overall risk: {overall:.2f}"

    return {
        "risk_spans": risk_spans,
        "summary": summary,
        "overall_risk": round(overall, 3),
    }
