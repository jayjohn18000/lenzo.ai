# app/utils/ask.py

import os
import asyncio
import httpx
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise EnvironmentError("Missing OPENROUTER_API_KEY in environment variables")

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost",
    "X-Title": "TruthRouter"
}

DEFAULT_ASK_MODELS = [
    "openai/gpt-3.5-turbo",
    "anthropic/claude-3-haiku",
    "mistralai/mistral-7b-instruct"
]

async def fetch_responses_from_models(prompt: str, models: List[str] = DEFAULT_ASK_MODELS):
    async with httpx.AsyncClient() as client:
        tasks = []
        for model in models:
            tasks.append(
                client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=HEADERS,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
            )

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for model, response in zip(models, responses):
            try:
                if isinstance(response, Exception):
                    raise response
                if response.status_code != 200:
                    raise ValueError(f"{response.status_code}: {response.text}")
                response_json = response.json()
                content = response_json["choices"][0]["message"]["content"]
                results.append({"model": model, "response": content})
            except Exception as e:
                print(f"[ERROR] Model {model} failed: {str(e)}")
                results.append({"model": model, "response": None})
        return results
