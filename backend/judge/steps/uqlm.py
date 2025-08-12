# backend/judge/steps/uqlm.py
from __future__ import annotations

import asyncio
import time
from typing import List

from backend.judge.schemas import Candidate
from backend.judge.clients.openrouter import llm_complete
from backend.judge.config import settings

# A small, tool-friendly system prompt to encourage sources/citations
UQLM_SYSTEM = (
    "You are a careful, citation-first assistant. "
    "Answer the user's question clearly and concisely. "
    "When making factual claims, include inline citations using URLs or simple [n] markers. "
    "Prefer reputable sources. If unsure, state uncertainty."
)

# Default tool-chain model; can be made configurable per request later
UQLM_MODEL = "openrouter/openai/gpt-4o"


async def _one(prompt: str, model: str) -> Candidate:
    t0 = time.perf_counter()
    text, meta = await llm_complete(model=model, prompt=prompt, system=UQLM_SYSTEM)
    dt = int((time.perf_counter() - t0) * 1000)
    return Candidate(
        text=text,
        provider="openrouter",
        model=model,
        tokens_in=meta.get("tokens_in", 0),
        tokens_out=meta.get("tokens_out", 0),
        gen_time_ms=dt,
    )


async def generate_with_uqlm(prompt: str, trace_id: str, n: int = 2) -> List[Candidate]:
    """
    Produce n drafts suitable for downstream verification.
    - Uses a single strong model for now (UQLM_MODEL).
    - Encourages citations to help RefChecker.
    - Returns surviving candidates only.
    """
    n = max(1, min(4, int(n)))  # small cap for cost
    tasks = [asyncio.create_task(_one(prompt, UQLM_MODEL)) for _ in range(n)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    cands: List[Candidate] = []
    for r in results:
        if isinstance(r, Candidate):
            cands.append(r)
    return cands
