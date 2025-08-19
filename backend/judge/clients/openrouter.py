# backend/judge/clients/openrouter.py - COMPLETE THIS FILE
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
                logger.info(f"Successfully received response")
                return response_data
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
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
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    
    try:
        response_data = await _post_chat(body)
        
        # Extract text from response
        if not response_data.get("choices"):
            raise OpenRouterError("No choices in response")
            
        choice = response_data["choices"][0]
        text = choice.get("message", {}).get("content", "")
        
        if not text:
            raise OpenRouterError("Empty response content")
        
        # Extract metadata
        usage = response_data.get("usage", {})
        meta = {
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": response_data.get("model", model),
        }
        
        return text.strip(), meta
        
    except OpenRouterError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in llm_complete: {e}")
        raise OpenRouterError(f"Unexpected error: {e}")


async def llm_judge(candidate: str, rubric: Dict[str, float], judge_model: str) -> Dict[str, float]:
    """
    Score a candidate response against rubric traits (0-1 scale).
    Returns: Dict[trait_name, score] where score is 0.0-1.0
    """
    traits_list = ", ".join(rubric.keys())
    
    system_prompt = f"""You are an expert evaluator. Score the following response on these traits: {traits_list}

Scoring scale: 0.0 (poor) to 1.0 (excellent)

Return ONLY a JSON object with scores. Example: {{"accuracy": 0.85, "clarity": 0.92}}
Do not include any other text or explanation."""

    prompt = f"""Response to evaluate:

{candidate}

Score this response on the following traits: {traits_list}

Return only JSON with scores 0.0-1.0."""
    
    try:
        text, _ = await llm_complete(model=judge_model, prompt=prompt, system=system_prompt)
        
        # Try to parse JSON response
        # Clean up common JSON formatting issues
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        scores = json.loads(cleaned_text)
        
        # Ensure all rubric traits are present and valid
        result = {}
        for trait in rubric:
            if trait in scores:
                try:
                    score = float(scores[trait])
                    result[trait] = max(0.0, min(1.0, score))  # Clamp to 0-1
                except (ValueError, TypeError):
                    result[trait] = 0.5  # neutral fallback
            else:
                result[trait] = 0.5  # missing trait fallback
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse judge response as JSON: {e}")
        # Fallback to neutral scores
        return {trait: 0.5 for trait in rubric}
    except Exception as e:
        logger.error(f"Error in llm_judge: {e}")
        # Fallback to neutral scores  
        return {trait: 0.5 for trait in rubric}