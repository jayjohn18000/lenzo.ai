# backend/dependencies.py
from __future__ import annotations

"""
Shared dependencies for Redis and DB across the API and worker.

- init_dependencies(redis_client, db_session_factory): called from main.py on startup
- get_job_manager(): FastAPI dependency used by API routes
- get_db_session(): optional generator dependency if you need raw DB sessions
"""

from typing import Callable, Optional, Generator, Any
import logging

import redis.asyncio as redis
from sqlalchemy.orm import Session, sessionmaker
from fastapi import HTTPException

from backend.jobs.manager import JobManager

logger = logging.getLogger(__name__)

# Module-level singletons
_redis_client: Optional[redis.Redis] = None
_db_session_factory: Optional[Callable[[], Session]] = None
_job_manager: Optional[JobManager] = None


def init_dependencies(
    redis_client: redis.Redis,
    db_session_factory: Optional[Callable[[], Session]] = None,
) -> JobManager:
    """
    Initialize shared dependencies and construct a JobManager instance.

    This should be called exactly once during app startup (see main.py).
    """
    global _redis_client, _db_session_factory, _job_manager

    if not isinstance(redis_client, redis.Redis):
        raise TypeError("init_dependencies expected a redis.asyncio.Redis instance")

    _redis_client = redis_client
    _db_session_factory = db_session_factory

    _job_manager = JobManager(redis_client=_redis_client, db_session_factory=_db_session_factory)
    logger.info("Dependencies initialized: redis=%s db_session_factory=%s", bool(_redis_client), bool(_db_session_factory))
    return _job_manager


# ---------- FastAPI dependencies ----------

def get_job_manager() -> JobManager:
    """
    FastAPI dependency to retrieve the shared JobManager.
    """
    if _job_manager is None:
        raise HTTPException(status_code=503, detail="Job system not initialized")
    return _job_manager


def get_db_session() -> Generator[Session, None, None]:
    """
    Optional dependency to yield a SQLAlchemy Session.

    Usage:
        @router.get("/something")
        def handler(session: Session = Depends(get_db_session)):
            ...
    """
    if _db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    session = None
    try:
        session = _db_session_factory()
        yield session
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


# ---------- Accessors for non-FastAPI code ----------

def get_redis_client() -> redis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return _redis_client


def get_db_session_factory() -> Callable[[], Session]:
    if _db_session_factory is None:
        raise RuntimeError("DB session factory is not initialized")
    return _db_session_factory
