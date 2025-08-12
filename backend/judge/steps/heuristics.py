# backend/judge/steps/heuristics.py
from typing import List
from backend.judge.schemas import Candidate

# quick-and-cheap red flags
REFUSAL_PHRASES = (
    "i cannot assist",
    "i can’t assist",
    "i cannot help",
    "as an ai",
    "i'm just an ai",
    "as a language model",
    "i am unable to",
    "cannot provide",
    "sorry, i can't",
    "i do not have access",
)

MIN_LEN = 40        # too short → likely low value
MAX_LEN = 6000      # extremely long → likely rambling
IDEAL_MIN = 200     # soft spot for many prompts
IDEAL_MAX = 1200

def _len_score(n: int) -> float:
    # piecewise: reward being within [IDEAL_MIN, IDEAL_MAX], penalize outside
    if n <= MIN_LEN:
        return 0.2
    if n >= MAX_LEN:
        return 0.3
    if IDEAL_MIN <= n <= IDEAL_MAX:
        return 1.0
    # gentle taper outside ideal band
    if n < IDEAL_MIN:
        return max(0.2, 0.6 + (n - MIN_LEN) / max(1, (IDEAL_MIN - MIN_LEN)) * 0.4)
    # n > IDEAL_MAX
    return max(0.3, 1.0 - (n - IDEAL_MAX) / max(1, (MAX_LEN - IDEAL_MAX)) * 0.7)

def _refusal_score(text: str) -> float:
    t = text.lower()
    return 0.0 if any(p in t for p in REFUSAL_PHRASES) else 1.0

def _format_score(text: str) -> float:
    # reward some structure (very rough)
    has_lists = "-" in text or "*" in text or "1." in text
    has_headers = "##" in text or "\n\n" in text
    return 0.8 + (0.1 if has_lists else 0.0) + (0.1 if has_headers else 0.0)

def score_heuristics(cands: List[Candidate]) -> List[Candidate]:
    """
    Assigns heuristic_score in [0,1] to each candidate.
    This is a low-cost signal used alongside judge scoring.
    """
    for c in cands:
        text = c.text or ""
        # base components
        ls = _len_score(len(text))
        rs = _refusal_score(text)
        fs = _format_score(text)
        # weighted blend (tuneable)
        score = 0.5 * ls + 0.35 * rs + 0.15 * fs
        c.heuristic_score = max(0.0, min(1.0, score))
    return cands
