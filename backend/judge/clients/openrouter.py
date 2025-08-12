# backend/judge/clients/openrouter.py
import json
from typing import Dict, List, Tuple
import httpx

from backend.judge.config import settings

OPENROUTER_URL = settings.OPENROUTER_API_URL
HEADERS = settings.OPENROUTER_HEADERS


class OpenRouterError(Exception):
    pass


async def _post_chat(body: Dict) -> Dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(OPENROUTER_URL, headers=HEADERS, json=body)
        if r.status_code >= 400:
            raise OpenRouterError(f"{r.status_code}: {r.text}")
        return r.json()


async def llm_complete(*, model: str, prompt: str, system: str | None = None) -> Tuple[str, Dict]:
    """
    Send a simple user-only (or system+user) chat to a specific model.
    Returns: (text, meta) where meta includes token usage if available.
    """
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {"model": model, "messages": messages}
    data = await _post_chat(body)

    # extract text + usage
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {}) or {}
    meta = {
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
        "model": model,
    }
    return text, meta


async def llm_judge(*, candidate: str, rubric: Dict[str, float], judge_model: str) -> Dict[str, float]:
    """
    Ask a judge model to score candidate on traits 0..1.
    We request strict JSON to simplify parsing; fallback returns flat 0.5s.
    """
    system = (
        "You are a precise evaluator. "
        "Return ONLY JSON mapping trait -> score in [0,1]. No prose."
    )
    prompt = (
        "Evaluate the following answer. For each trait in the set, "
        "produce a float score in [0,1]. Traits (with weights) are:\n"
        f"{json.dumps(rubric)}\n\n"
        "Answer:\n"
        f"{candidate}\n\n"
        "Return strictly a JSON object like: {\"accuracy\": 0.92, ...}"
    )

    text, _ = await llm_complete(model=judge_model, prompt=prompt, system=system)
    try:
        scores = json.loads(text)
        # clamp
        for k, v in list(scores.items()):
            scores[k] = max(0.0, min(1.0, float(v)))
        return scores
    except Exception:
        # permissive fallback
        return {k: 0.5 for k in rubric.keys()}
