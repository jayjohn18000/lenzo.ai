# backend/jobs/worker.py
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.jobs.manager import JobManager
from backend.jobs.models import JobStatus, QueryJob, JobRecord

logger = logging.getLogger(__name__)


class QueryWorker:
    """
    Redis-driven job worker.

    Contract:
      - BRPOP from "query_jobs:pending"
      - Load job payload from Redis `job_data:{id}`; if missing, fall back to DB JobRecord
      - Write results to `job_result:{id}`
      - Update status JSON at `job:{id}:status`
      - Publish "jobs:completed" / "jobs:failed"
    """

    def __init__(self, job_manager: JobManager, worker_id: int = 1):
        self.job_manager = job_manager
        self.worker_id = worker_id
        self.running = False

    async def start(self) -> None:
        """Start processing jobs from the Redis queue."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")

        while self.running:
            try:
                # With decode_responses=True, returns [list_name, job_id] (both str) or None
                popped = await self.job_manager.redis.brpop("query_jobs:pending", timeout=5)
                if not popped:
                    continue

                job_id = popped[1]

                # Skip if cancelled before we pick it up
                if await self._is_cancelled(job_id):
                    logger.info(f"Worker {self.worker_id}: job {job_id} already cancelled, skipping")
                    continue

                await self.process_job(job_id)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} loop error: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Signal the worker loop to exit."""
        self.running = False

    async def process_job(self, job_id: str) -> None:
        """Process a single job by ID."""
        logger.info(f"Worker {self.worker_id} processing job {job_id}")

        # Load job payload (prefer Redis, fallback to DB)
        job_obj = await self._load_job(job_id)
        if not job_obj:
            logger.error(f"Worker {self.worker_id}: job {job_id} not found in cache/DB")
            await self._set_status(job_id, {"id": job_id, "status": JobStatus.FAILED.value, "error": "not_found"})
            await self.job_manager.redis.publish("jobs:failed", job_id)
            return

        started_at = datetime.now(timezone.utc).isoformat()

        # Mark as processing
        await self._set_status(
            job_id,
            {"id": job_id, "status": JobStatus.PROCESSING.value, "started_at": started_at},
        )

        # Respect cancellation just before execution
        if await self._is_cancelled(job_id):
            await self._set_status(job_id, {"id": job_id, "status": JobStatus.CANCELLED.value})
            logger.info(f"Worker {self.worker_id}: job {job_id} cancelled before run")
            return

        try:
            # Execute pipeline
            result = await job_obj.process()

            # Persist result to Redis for the API to read
            await self.job_manager.redis.set(f"job_result:{job_id}", json.dumps(result))

            completed_at = datetime.now(timezone.utc).isoformat()
            # Compute elapsed if possible
            status_payload = {
                "id": job_id,
                "status": JobStatus.COMPLETED.value,
                "completed_at": completed_at,
            }

            # Final status
            await self._set_status(job_id, status_payload)

            # DB update (optional)
            if self.job_manager.db_session_factory:
                try:
                    with self.job_manager.db_session_factory() as session:  # type: ignore[call-arg]
                        self._update_db_success(session, job_id, result, started_at, completed_at)
                except Exception as db_err:
                    logger.warning(f"DB success update failed for {job_id}: {db_err}")

            # Publish completion
            await self.job_manager.redis.publish("jobs:completed", job_id)

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: job {job_id} failed: {e}")
            completed_at = datetime.now(timezone.utc).isoformat()
            err_payload = {
                "id": job_id,
                "status": JobStatus.FAILED.value,
                "error": f"{type(e).__name__}: {e}",
                "completed_at": completed_at,
            }
            await self._set_status(job_id, err_payload)

            # DB update (optional)
            if self.job_manager.db_session_factory:
                try:
                    with self.job_manager.db_session_factory() as session:  # type: ignore[call-arg]
                        self._update_db_failure(session, job_id, str(e), started_at, completed_at)
                except Exception as db_err:
                    logger.warning(f"DB failure update failed for {job_id}: {db_err}")

            await self.job_manager.redis.publish("jobs:failed", job_id)

    # -----------------
    # Helper utilities
    # -----------------

    async def _load_job(self, job_id: str) -> Optional[QueryJob]:
        """Load job payload: Redis first, DB JobRecord fallback."""
        # Redis cache
        job_data_raw = await self.job_manager.redis.get(f"job_data:{job_id}")
        if job_data_raw:
            data = json.loads(job_data_raw)
            return QueryJob(
                request_id=data["request_id"],
                prompt=data["prompt"],
                mode=data.get("mode", "balanced"),
                max_models=int(data.get("max_models", 3)),
                trace_id=data.get("trace_id", ""),
            )

        # DB fallback (never query the dataclass)
        if self.job_manager.db_session_factory:
            try:
                with self.job_manager.db_session_factory() as session:  # type: ignore[call-arg]
                    rec = session.get(JobRecord, job_id)  # ✅ correct ORM lookup
                    if rec:
                        return QueryJob(
                            request_id=rec.request_id,
                            prompt=rec.prompt,
                            mode=rec.mode or "balanced",
                            max_models=int(rec.max_models or 3),
                            trace_id=rec.trace_id or "",
                        )
            except Exception as db_err:
                logger.warning(f"DB lookup failed for job {job_id}: {db_err}")

        return None

    def _update_db_success(
        self, session: Session, job_id: str, result: dict, started_at_iso: str, completed_at_iso: str
    ) -> None:
        rec = session.get(JobRecord, job_id)
        if not rec:
            return
        rec.status = JobStatus.COMPLETED.value
        rec.result = result
        try:
            started = datetime.fromisoformat(started_at_iso) if started_at_iso else None
            completed = datetime.fromisoformat(completed_at_iso) if completed_at_iso else None
        except Exception:
            started = completed = None
        rec.started_at = started or rec.started_at
        rec.completed_at = completed or rec.completed_at
        if started and completed:
            rec.actual_time_ms = (completed - started).total_seconds() * 1000.0
        rec.error = None
        session.add(rec)
        session.commit()

    def _update_db_failure(self, session: Session, job_id: str, error: str, started_at_iso: str, completed_at_iso: str) -> None:
        rec = session.get(JobRecord, job_id)
        if not rec:
            return
        rec.status = JobStatus.FAILED.value
        rec.error = error
        try:
            started = datetime.fromisoformat(started_at_iso) if started_at_iso else None
            completed = datetime.fromisoformat(completed_at_iso) if completed_at_iso else None
        except Exception:
            started = completed = None
        rec.started_at = started or rec.started_at
        rec.completed_at = completed or rec.completed_at
        if started and completed:
            rec.actual_time_ms = (completed - started).total_seconds() * 1000.0
        session.add(rec)
        session.commit()

    async def _is_cancelled(self, job_id: str) -> bool:
        cached = await self.job_manager.redis.get(f"job:{job_id}:status")
        if not cached:
            return False
        try:
            st = json.loads(cached)
            return (st.get("status") or "").lower() == JobStatus.CANCELLED.value
        except Exception:
            return False

    async def _set_status(self, job_id: str, payload: dict) -> None:
        await self.job_manager.redis.set(f"job:{job_id}:status", json.dumps(payload))
