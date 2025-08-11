# backend/main.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from backend.utils.ask import fetch_responses_from_models
from backend.utils.judge import score_responses

load_dotenv()

backend = FastAPI()

backend.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResponseItem(BaseModel):
    model: str
    response: Optional[str] = None


class RouteInput(BaseModel):
    prompt: str
    responses: List[ResponseItem]
    judge_models: List[str]
    use_ask: Optional[bool] = False


@backend.post("/route")
async def route_llms(data: RouteInput):
    responses = data.responses

    if data.use_ask:
        raw_responses = await fetch_responses_from_models(data.prompt)
        responses = [ResponseItem(**r) for r in raw_responses]

    valid_responses = [r for r in responses if r.response]
    if not valid_responses:
        return {
            "prompt": data.prompt,
            "responses": [r.dict() for r in responses],
            "error": "No valid responses to score."
        }

    result = await score_responses(
        responses=[r.dict() for r in valid_responses],
        judge_models=data.judge_models,
        prompt=data.prompt
    )

    return {
        "prompt": data.prompt,
        "responses": [r.dict() for r in responses],
        **result
    }
