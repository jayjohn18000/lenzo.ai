# backend/jobs/worker.py
import asyncio
import logging
from datetime import datetime
from backend.jobs.manager import JobManager
from backend.jobs.models import JobStatus

logger = logging.getLogger(__name__)

class QueryWorker:
    def __init__(self, job_manager: JobManager, worker_id: int = 1):
        self.job_manager = job_manager
        self.worker_id = worker_id
        self.running = False
        
    async def start(self):
        """Start processing jobs from queue"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self.running:
            try:
                # Fetch job from Redis queue (blocking)
                job_id = await self.job_manager.redis.brpop(
                    "query_jobs:pending", 
                    timeout=5
                )
                
                if job_id:
                    await self.process_job(job_id[1].decode())
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def process_job(self, job_id: str):
        """Process a single job"""
        logger.info(f"Processing job {job_id}")
        
        with self.job_manager.db_session_factory() as session:
            job = session.query(QueryJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update status
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            session.commit()
        
        try:
            # Run the actual pipeline
            from backend.judge.schemas import RouteRequest
            
            request = RouteRequest(**job.request_params)
            result = await run_pipeline(request)
            
            # Store results
            with self.job_manager.db_session_factory() as session:
                job = session.query(QueryJob).filter_by(id=job_id).first()
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.actual_time_ms = (job.completed_at - job.started_at).total_seconds() * 1000
                job.result = result.model_dump()
                session.commit()
            
            # Publish completion event
            await self.job_manager.redis.publish("jobs:completed", job_id)
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            
            with self.job_manager.db_session_factory() as session:
                job = session.query(QueryJob).filter_by(id=job_id).first()
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                session.commit()