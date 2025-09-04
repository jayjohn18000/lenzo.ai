# backend/jobs/manager.py - FIXED VERSION
import uuid
import asyncio
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from backend.jobs.models import QueryJob, JobStatus
from backend.judge.pipelines.runner import run_pipeline
import redis.asyncio as redis

class JobManager:
    def __init__(self, redis_client: redis.Redis, db_session_factory):
        self.redis = redis_client
        self.db_session_factory = db_session_factory
        self.processing_queue = asyncio.Queue()
        
    async def create_job(self, job_params: Dict[str, Any]) -> str:
    """Create a new job with correct parameter structure"""
    
    # Option A: If QueryJob expects flat parameters
    try:
        from backend.jobs.types import QueryJob
        
        # Create job directly with parameters
        job = QueryJob(**job_params)
        
        # Store job in your storage system
        await self.store_job(job)
        
        return job.request_id
        
    except TypeError as e:
        # Log the error for debugging
        print(f"QueryJob creation error: {e}")
        print(f"Attempted params: {job_params}")
        raise
        
        # For database persistence (if you have SQLAlchemy models)
        # with self.db_session_factory() as session:
        #     db_job = DatabaseQueryJob(
        #         id=job_id,
        #         prompt=request_params['prompt'],
        #         request_params=request_params,
        #         status=JobStatus.PENDING
        #     )
        #     session.add(db_job)
        #     session.commit()
        
        # Add to Redis queue for workers
        await self.redis.lpush("query_jobs:pending", job_id)
        
        # Store job data in Redis for worker access
        job_data = {
            "request_id": job_id,
            "prompt": request_params['prompt'],
            "mode": request_params.get('mode', 'balanced'),
            "max_models": request_params.get('max_models', 3),
            "trace_id": request_params.get('trace_id', '')
        }
        await self.redis.set(f"job_data:{job_id}", json.dumps(job_data))
        
        # Publish event for real-time updates
        await self.redis.publish("jobs:created", job_id)
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status with caching"""
        # Check Redis cache first
        cached = await self.redis.get(f"job:{job_id}:status")
        if cached:
            return json.loads(cached)
        
        # Check if job result is available
        result = await self.redis.get(f"job_result:{job_id}")
        if result:
            return {
                "id": job_id,
                "status": "completed",
                "result": json.loads(result)
            }
        
        # Check if job is in queue
        queue_length = await self.redis.llen("query_jobs:pending")
        if queue_length > 0:
            return {
                "id": job_id,
                "status": "pending",
                "queue_position": "estimated"
            }
        
        return {
            "id": job_id,
            "status": "processing",
            "progress": "in_progress"
        }