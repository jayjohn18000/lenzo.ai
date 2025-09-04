# backend/jobs/worker.py
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from backend.jobs.manager import JobManager
from backend.jobs.models import JobStatus, QueryJob, JobRecord

logger = logging.getLogger(__name__)


def _b2s(val) -> str:
    """Decode redis bytes to str if needed."""
    if isinstance(val, (bytes, bytearray)):
        return val.decode("utf-8")
    return str(val)


class QueryWorker:
    """
    Background worker that pulls jobs from Redis and executes them.

    Behavior:
      - BRPOP from 'query_jobs:pending'
      - Load payload from Redis 'job_data:<id>'; fallback to DB JobRecord if configured
      - Update Redis status keys through the lifecycle
      - Persist completion/failure back to DB if available
      - Publish notifications on 'jobs:completed' / 'jobs:failed'
    """

    def __init__(self, job_manager: JobManager, worker_id: int = 1):
        self.job_manager = job_manager
        self.worker_id = worker_id
        self.running = False

    async def start(self):
        """Start processing jobs from the Redis queue."""
        self.running = True
        logger.info("Worker %s started", self.worker_id)

        while self.running:
            try:
                # brpop blocks up to timeout seconds; returns (list, value) or None
                popped = await self.job_manager.redis.brpop("query_jobs:pending", timeout=5)
                if not popped:
                    continue  # idle tick

                job_id = _b2s(popped[1])

                # Skip if cancelled before we pick it up
                if await self._is_cancelled(job_id):
                    logger.info("Worker %s: job %s already cancelled, skipping", self.worker_id, job_id)
                    # Optionally mirror cancellation to DB if present
                    await self._maybe_update_db_status(job_id, JobStatus.CANCELLED.value)
                    continue

                await self.process_job(job_id)

            except Exception as e:
                logger.exception("Worker %s loop error: %s", self.worker_id, e)
                await asyncio.sleep(1)

    async def stop(self):
        """Signal the worker loop to exit."""
        self.running = False

    async def process_job(self, job_id: str):
        """Process a single job by ID."""
        logger.info("Worker %s processing job %s", self.worker_id, job_id)

        # Load job payload for execution (prefer Redis cache, fall back to DB if available)
        job_obj: Optional[QueryJob] = await self._load_job(job_id)

        if not job_obj:
            logger.error("Worker %s: job %s not found in cache/DB", self.worker_id, job_id)
            await self._set_status(
                job_id,
                {
                    "id": job_id,
                    "status": JobStatus.FAILED.value,
                    "error": "not_found",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.job_manager.redis.publish("jobs:failed", job_id)
            return

        # Mark as processing
        started_at = datetime.now(timezone.utc)
        await self._set_status(
            job_id,
            {
                "id": job_id,
                "status": JobStatus.PROCESSING.value,
                "started_at": started_at.isoformat(),
            },
        )
        await self._maybe_update_db_status(job_id, JobStatus.PROCESSING.value, started_at=started_at)

        # Respect cancellation just before execution
        if await self._is_cancelled(job_id):
            await self._set_status(job_id, {"id": job_id, "status": JobStatus.CANCELLED.value})
            await self._maybe_update_db_status(job_id, JobStatus.CANCELLED.value)
            logger.info("Worker %s: job %s cancelled before run", self.worker_id, job_id)
            return

        try:
            # Execute using the model-layer helper (which calls your pipeline)
            result = await job_obj.process()

            # Persist result to Redis for the API to read
            await self.job_manager.redis.set(f"job_result:{job_id}", json.dumps(result))

            # Final status
            completed_at = datetime.now(timezone.utc)
            await self._set_status(
                job_id,
                {
                    "id": job_id,
                    "status": JobStatus.COMPLETED.value,
                    "completed_at": completed_at.isoformat(),
                },
            )

            # Persist to DB if available
            await self._maybe_update_db_completion(job_id, status=JobStatus.COMPLETED.value, result=result, completed_at=completed_at)

            # Publish completion
            await self.job_manager.redis.publish("jobs:completed", job_id)

        except Exception as e:
            logger.exception("Worker %s: job %s failed: %s", self.worker_id, job_id, e)
            completed_at = datetime.now(timezone.utc).isoformat()
            await self._set_status(
                job_id,
                {
                    "id": job_id,
                    "status": JobStatus.FAILED.value,
                    "error": f"{type(e).__name__}: {e}",
                    "completed_at": completed_at,
                },
            )
            # Persist failure to DB if available
            await self._maybe_update_db_failure(job_id, error=f"{type(e).__name__}: {e}")
            await self.job_manager.redis.publish("jobs:failed", job_id)

    # -----------------
    # Helper utilities
    # -----------------

    async def _load_job(self, job_id: str) -> Optional[QueryJob]:
        """Load QueryJob from Redis; if missing and DB is configured, fallback to DB JobRecord."""
        job_data_raw = await self.job_manager.redis.get(f"job_data:{job_id}")
        if job_data_raw:
            try:
                data = json.loads(_b2s(job_data_raw))
                return QueryJob(
                    request_id=data["request_id"],
                    prompt=data["prompt"],
                    mode=data.get("mode", "balanced"),
                    max_models=int(data.get("max_models", 3)),
                    trace_id=data.get("trace_id", "") or "",
                )
            except Exception as e:
                logger.warning("Worker %s: bad job_data for %s: %s", self.worker_id, job_id, e)

        # DB fallback (never query QueryJob via SQLAlchemy)
        if self.job_manager.db_session_factory:
            try:
                with self.job_manager.db_session_factory() as session:
                    rec = session.get(JobRecord, job_id)
                    if rec:
                        return QueryJob.from_record(rec)
            except Exception as db_err:
                logger.warning("DB lookup failed for job %s: %s", job_id, db_err)

        return None

    async def _is_cancelled(self, job_id: str) -> bool:
        cached = await self.job_manager.redis.get(f"job:{job_id}:status")
        if not cached:
            return False
        try:
            st = json.loads(_b2s(cached))
            return (st.get("status") or "").lower() == JobStatus.CANCELLED.value
        except Exception:
            return False

    async def _set_status(self, job_id: str, payload: dict):
        await self.job_manager.redis.set(f"job:{job_id}:status", json.dumps(payload))

    async def _maybe_update_db_status(self, job_id: str, status: str, *, started_at: Optional[datetime] = None):
        """Update just the status (and optionally started_at) in DB if session factory is configured."""
        if not self.job_manager.db_session_factory:
            return
        try:
            with self.job_manager.db_session_factory() as session:
                rec = session.get(JobRecord, job_id)
                if rec:
                    rec.status = status
                    if started_at:
                        rec.started_at = started_at
                    session.commit()
        except Exception as e:
            logger.warning("Failed to update DB status for %s: %s", job_id, e)

    async def _maybe_update_db_completion(
        self,
        job_id: str,
        *,
        status: str,
        result: dict,
        completed_at: datetime,
    ):
        if not self.job_manager.db_session_factory:
            return
        try:
            with self.job_manager.db_session_factory() as session:
                rec = session.get(JobRecord, job_id)
                if rec:
                    rec.status = status
                    rec.completed_at = completed_at
                    rec.result = result
                    # If available, store elapsed time
                    try:
                        # prefer response_time_ms from result if present
                        rt = result.get("response_time_ms")
                        if isinstance(rt, (int, float)):
                            rec.actual_time_ms = float(rt)
                    except Exception:
                        pass
                    session.commit()
        except Exception as e:
            logger.warning("Failed to persist DB completion for %s: %s", job_id, e)

    async def _maybe_update_db_failure(self, job_id: str, *, error: str):
        if not self.job_manager.db_session_factory:
            return
        try:
            with self.job_manager.db_session_factory() as session:
                rec = session.get(JobRecord, job_id)
                if rec:
                    rec.status = JobStatus.FAILED.value
                    rec.error = error
                    rec.completed_at = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.warning("Failed to persist DB failure for %s: %s", job_id, e)
