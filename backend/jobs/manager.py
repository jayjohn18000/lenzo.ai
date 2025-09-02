# backend/jobs/manager.py
import uuid
import asyncio
from typing import Optional, Dict
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
        
    async def create_job(self, request_params: Dict) -> str:
        """Create a new job and return job_id"""
        job_id = str(uuid.uuid4())
        
        with self.db_session_factory() as session:
            job = QueryJob(
                id=job_id,
                prompt=request_params['prompt'],
                request_params=request_params,
                status=JobStatus.PENDING
            )
            session.add(job)
            session.commit()
        
        # Add to Redis queue for workers
        await self.redis.lpush("query_jobs:pending", job_id)
        
        # Publish event for real-time updates
        await self.redis.publish("jobs:created", job_id)
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status with caching"""
        # Check Redis cache first
        cached = await self.redis.get(f"job:{job_id}:status")
        if cached:
            return json.loads(cached)
        
        # Fallback to database
        with self.db_session_factory() as session:
            job = session.query(QueryJob).filter_by(id=job_id).first()
            if not job:
                return None
            
            status_data = {
                "id": job.id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "result": job.result,
                "error": job.error,
                "progress": self._calculate_progress(job)
            }
            
            # Cache for 60 seconds
            await self.redis.setex(
                f"job:{job_id}:status", 
                60, 
                json.dumps(status_data)
            )
            
            return status_data
    
    def _calculate_progress(self, job: QueryJob) -> float:
        """Calculate job progress percentage"""
        if job.status == JobStatus.COMPLETED:
            return 100.0
        elif job.status == JobStatus.PROCESSING:
            # Estimate based on typical processing time
            if job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                estimated = (job.estimated_time_ms or 3000) / 1000
                return min(95.0, (elapsed / estimated) * 100)
        return 0.0