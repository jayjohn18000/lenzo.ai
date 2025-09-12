# backend/judge/steps/heuristics.py
"""
Heuristic scoring for candidate responses
"""

import re
import logging
from typing import List
from backend.judge.schemas import Candidate

logger = logging.getLogger(__name__)


def score_heuristics(candidates: List[Candidate]) -> List[Candidate]:
    """
    Apply heuristic scoring to candidates based on response quality signals
    """
    for candidate in candidates:
        candidate.heuristic_score = _calculate_heuristic_score(candidate)

    return candidates


def _calculate_heuristic_score(candidate: Candidate) -> float:
    """
    Calculate heuristic score based on multiple quality signals
    """
    if not candidate.text:
        return 0.0

    text = candidate.text.strip()
    score = 0.5  # Start with neutral score

    # Length-based scoring
    length_score = _score_length(text)

    # Refusal detection
    refusal_penalty = _detect_refusal(text)

    # Coherence signals
    coherence_score = _score_coherence(text)

    # Error and placeholder detection
    error_penalty = _detect_errors(text)

    # Combine scores
    score = (
        length_score * 0.3
        + coherence_score * 0.4
        + (1.0 - refusal_penalty) * 0.2
        + (1.0 - error_penalty) * 0.1
    )

    return max(0.0, min(1.0, score))


def _score_length(text: str) -> float:
    """Score based on response length (sweet spot around 200-800 chars)"""
    length = len(text)

    if length < 20:
        return 0.1  # Too short
    elif length < 50:
        return 0.3
    elif length < 100:
        return 0.6
    elif length < 300:
        return 0.9  # Good length
    elif length < 800:
        return 1.0  # Optimal length
    elif length < 1500:
        return 0.8  # Getting long
    else:
        return 0.6  # Too long


def _detect_refusal(text: str) -> float:
    """Detect if the model refused to answer (0.0 = no refusal, 1.0 = clear refusal)"""
    text_lower = text.lower()

    refusal_patterns = [
        r"i can't|i cannot|i'm not able",
        r"i don't know|i'm not sure|i'm uncertain",
        r"i'm sorry, but|sorry, i can't",
        r"as an ai|as a language model",
        r"i'm not allowed|i cannot provide",
        r"against my guidelines|policy",
    ]

    refusal_score = 0.0
    for pattern in refusal_patterns:
        if re.search(pattern, text_lower):
            refusal_score += 0.2

    return min(1.0, refusal_score)


def _score_coherence(text: str) -> float:
    """Score text coherence based on structure and flow"""
    sentences = text.split(".")
    sentence_count = len([s for s in sentences if s.strip()])

    # Sentence structure score
    if sentence_count == 0:
        return 0.0
    elif sentence_count == 1:
        return 0.6
    elif sentence_count <= 5:
        return 0.9
    else:
        return 0.8


def _detect_errors(text: str) -> float:
    """Detect obvious errors or placeholder text"""
    error_patterns = [
        r"\[ERROR\]|\[PLACEHOLDER\]",
        r"undefined|null|NaN",
        r"lorem ipsum",
        r"test test test",
        r"TODO:|FIXME:",
    ]

    error_score = 0.0
    text_lower = text.lower()

    for pattern in error_patterns:
        if re.search(pattern, text_lower):
            error_score += 0.3

    return min(1.0, error_score)
