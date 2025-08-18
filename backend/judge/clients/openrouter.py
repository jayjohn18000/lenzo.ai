# backend/judge/clients/openrouter.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

import httpx

from backend.judge.config import settings

logger = logging.getLogger(__name__)

# Base URL from settings (e.g., https://openrouter.ai/api/v1)
OPENROUTER_BASE: str = str(settings.openrouter_api_url)
CHAT_COMPLETIONS_URL: str = f"{OPENROUTER_BASE}/chat/completions"
HEADERS: Dict[str, str] = settings.openrouter_headers()
TIMEOUT: float = settings.request_timeout_seconds


class OpenRouterError(Exception):
    """Raised for non-2xx responses or malformed payloads from OpenRouter."""


async def _post_chat(body: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Making request to {CHAT_COMPLETIONS_URL}")
    logger.info(f"Request body model: {body.get('model')}")
    logger.info(f"Request headers: {dict(HEADERS)}")  # Don't log the actual API key
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(CHAT_COMPLETIONS_URL, headers=HEADERS, json=body)
            logger.info(f"Response status: {r.status_code}")
            
            # Standardize error propagation with body text for debugging
            if r.status_code >= 400:
                detail = r.text
                logger.error(f"OpenRouter API error {r.status_code}: {detail}")
                raise OpenRouterError(f"{r.status_code}: {detail}")
            
            try:
                response_data = r.json()
                logger.info(f"Successfully received response with {len(str(response_data))} chars")
                return response_data
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {r.text[:500]}")
                raise OpenRouterError(f"Invalid JSON from OpenRouter: {e}")
                
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise OpenRouterError(f"Request timeout: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise OpenRouterError(f"Request error: {e}")


async def llm_complete(
    *,
    model: str,
    prompt: str,
    system: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Send a simple user-only (or system+user) chat to a specific model.
    Returns: (text, meta) where meta includes token usage if available.
    """
    logger.info(f"Starting completion for model: {model}")
    
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    data = await _post_chat(body)

    # Robust extraction: OpenRouter mirrors OpenAI response shape
    try:
        text = data["choices"][0]["message"]["content"]
        if not text:
            logger.warning(f"Empty response text for model {model}")
            text = ""
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Unexpected response format for model {model}: {e}")
        logger.error(f"Response data: {json.dumps(data, indent=2)[:500]}")
        raise OpenRouterError(f"Unexpected response format (no choices[0].message.content): {e}\nPayload: {json.dumps(data)[:500]}")

    usage = data.get("usage") or {}
    meta: Dict[str, Any] = {
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
        "model": data.get("model", model),
        "id": data.get("id"),
    }
    
    logger.info(f"Completion successful for {model}: {len(text)} chars, {meta['tokens_in']} in, {meta['tokens_out']} out")
    return text, meta


async def llm_judge(
    *,
    candidate: str,
    rubric: Dict[str, float],
    judge_model: str,
) -> Dict[str, float]:
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
        # Clamp to [0,1] and fill any missing keys
        clean: Dict[str, float] = {}
        for k in rubric.keys():
            v = float(scores.get(k, 0.5))
            clean[k] = max(0.0, min(1.0, v))
        return clean
    except Exception as e:
        logger.warning(f"Judge model returned non-JSON, using fallback: {e}")
        # Permissive fallback if judge outputs non-JSON
        return {k: 0.5 for k in rubric.keys()}