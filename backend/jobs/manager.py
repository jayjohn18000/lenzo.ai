# backend/jobs/manager.py
from __future__ import annotations

import uuid
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable

import redis.asyncio as redis
from sqlalchemy.orm import Session

from backend.jobs.models import QueryJob, JobStatus, JobRecord

logger = logging.getLogger(__name__)


class JobManager:
    """
    Coordinates job creation, caching in Redis, optional DB persistence,
    and queueing for background workers.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        db_session_factory: Optional[Callable[[], Session]],
    ):
        self.redis = redis_client
        self.db_session_factory = db_session_factory
        # kept for backwards-compatibility if something uses it
        self.processing_queue = asyncio.Queue()

    async def create_job(self, job_params: Dict[str, Any]) -> str:
        """
        Create a new job, persist minimal metadata, enqueue it for processing,
        and return the job's request_id.
        """
        # Ensure we have an ID and required fields
        job_id = job_params.get("request_id") or str(uuid.uuid4())
        if "prompt" not in job_params or not job_params["prompt"]:
            raise ValueError("Missing required field: 'prompt'")

        # Normalize params to match QueryJob dataclass
        payload = {
            "request_id": job_id,
            "prompt": job_params["prompt"],
            "mode": job_params.get("mode", "balanced"),
            "max_models": int(job_params.get("max_models", 3)),
            "trace_id": job_params.get("trace_id", ""),
        }

        # Construct the job object (validates fields)
        try:
            job = QueryJob(**payload)
        except TypeError as e:
            raise ValueError(f"Invalid job parameters: {e}") from e

        # Optional: persist via DB session factory if your ORM layer exists
        await self._maybe_persist_to_db(job)

        # Persist minimal job state and enqueue for workers
        await self._store_job_to_cache(job)
        await self.redis.lpush("query_jobs:pending", job.request_id)
        await self.redis.publish("jobs:created", job.request_id)

        return job.request_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status from cache, result, or queue heuristics."""
        # 1) Cached live status
        cached = await self.redis.get(f"job:{job_id}:status")
        if cached:
            return json.loads(cached)

        # 2) Completed result present
        result = await self.redis.get(f"job_result:{job_id}")
        if result:
            return {
                "id": job_id,
                "status": JobStatus.COMPLETED.value,
                "result": json.loads(result),
            }

        # 3) Heuristic: pending if queue has items (we don't scan full list here)
        queue_length = await self.redis.llen("query_jobs:pending")
        if queue_length and queue_length > 0:
            return {
                "id": job_id,
                "status": JobStatus.PENDING.value,
                "queue_position": "estimated",
            }

        # 4) Fallback: assume processing
        return {
            "id": job_id,
            "status": JobStatus.PROCESSING.value,
            "progress": "in_progress",
        }

    async def cancel_job(self, job_id: str) -> None:
        """Mark a job as cancelled and publish an event (worker should honor this)."""
        status = {"id": job_id, "status": JobStatus.CANCELLED.value}
        await self.redis.set(f"job:{job_id}:status", json.dumps(status))
        await self.redis.publish("jobs:cancelled", job_id)

    # ------------------------
    # Internal helper methods
    # ------------------------

    async def _store_job_to_cache(self, job: QueryJob) -> None:
        """Write initial status and job data to Redis."""
        created_at = datetime.now(timezone.utc).isoformat()

        # Initial status
        await self.redis.set(
            f"job:{job.request_id}:status",
            json.dumps(
                {
                    "id": job.request_id,
                    "status": JobStatus.PENDING.value,
                    "created_at": created_at,  # include ISO8601 timestamp per spec
                }
            ),
        )
        # Job data for worker
        job_data = {
            "request_id": job.request_id,
            "prompt": job.prompt,
            "mode": job.mode,
            "max_models": job.max_models,
            "trace_id": job.trace_id,
            "created_at": created_at,
        }
        await self.redis.set(f"job_data:{job.request_id}", json.dumps(job_data))

    async def _maybe_persist_to_db(self, job: QueryJob) -> None:
        """
        Optional DB persistence. Inserts or merges a JobRecord and commits.
        No-ops if a session factory isn't configured.
        """
        if not self.db_session_factory:
            return

        try:
            with self.db_session_factory() as session:
                rec = session.get(JobRecord, job.request_id)
                if rec is None:
                    rec = JobRecord(
                        request_id=job.request_id,
                        prompt=job.prompt,
                        mode=job.mode,
                        max_models=job.max_models,
                        trace_id=job.trace_id or None,
                        status=JobStatus.PENDING.value,
                    )
                    session.add(rec)
                else:
                    # Merge/refresh inputs without clobbering status/timestamps/result
                    rec.apply_from_job(job)
                    # keep status as-is unless it's missing
                    if not rec.status:
                        rec.status = JobStatus.PENDING.value
                session.commit()
        except Exception as e:
            # Gate DB failures so queueing still works
            logger.warning("Job DB persistence failed for %s: %s", job.request_id, e)
            return
