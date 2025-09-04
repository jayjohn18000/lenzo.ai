# backend/jobs/models.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import time
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.schemas import RouteRequest, RouteOptions
from sqlalchemy import Column, String, DateTime, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

# SQLAlchemy Base for job persistence models
Base = declarative_base()

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class QueryJob:
    """Job for processing query requests asynchronously"""
    request_id: str
    prompt: str
    mode: str = "balanced"
    max_models: int = 3
    trace_id: str = ""
    
    async def process(self) -> Dict[str, Any]:
        """Process the query job"""
        try:
            # Create RouteRequest from job data
            route_request = RouteRequest(
                prompt=self.prompt,
                options=RouteOptions(
                    model_selection_mode=self.mode,
                    max_parallel_requests=self.max_models
                )
            )
            
            # Run the pipeline
            result = await run_pipeline(
                pipeline_id="judge",  # or determine dynamically
                req=route_request,
                trace_id=self.trace_id
            )
            
            return {
                "request_id": self.request_id,
                "answer": result.get("answer", ""),
                "confidence": result.get("confidence", 0.0),
                "winner_model": result.get("winner_model", ""),
                "response_time_ms": result.get("response_time_ms", 0),
                "models_used": result.get("models_attempted", []),
                "status": "completed"
            }
            
        except Exception as e:
            return {
                "request_id": self.request_id,
                "error": str(e),
                "status": "failed"
            }