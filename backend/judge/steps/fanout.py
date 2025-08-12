# backend/judge/steps/fanout.py
import asyncio
import time
from typing import List, Optional

from backend.judge.schemas import Candidate
from backend.judge.clients.openrouter import llm_complete, OpenRouterError
from backend.judge.config import settings


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for m in items:
        if m not in seen:
            out.append(m)
            seen.add(m)
    return out


async def _gen_one(model: str, prompt: str, sem: asyncio.Semaphore) -> Optional[Candidate]:
    async with sem:
        t0 = time.perf_counter()
        try:
            text, meta = await llm_complete(model=model, prompt=prompt)
            dt_ms = int((time.perf_counter() - t0) * 1000)
            return Candidate(
                text=text,
                provider="openrouter",
                model=model,
                tokens_in=meta.get("tokens_in", 0),
                tokens_out=meta.get("tokens_out", 0),
                gen_time_ms=dt_ms,
            )
        except (OpenRouterError, Exception) as e:
            # Soft-fail this branch; caller will proceed with surviving candidates
            # You can hook in structured logging here if desired.
            return None


async def fanout_generate(prompt: str, models: List[str], trace_id: str) -> List[Candidate]:
    """
    Generate candidate answers in parallel across models.
    Honors MAX_PARALLEL_FANOUT; filters out failures; preserves input order.
    """
    models = _dedupe_preserve_order(models)[: max(1, settings.MAX_PARALLEL_FANOUT * 4)]
    sem = asyncio.Semaphore(max(1, settings.MAX_PARALLEL_FANOUT))

    tasks = [asyncio.create_task(_gen_one(m, prompt, sem)) for m in models]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # keep successful candidates only, preserve order
    candidates: List[Candidate] = [r for r in results if isinstance(r, Candidate)]
    return candidates
