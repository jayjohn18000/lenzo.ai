# backend/dependencies.py
"""
Dependency injection for FastAPI endpoints
"""

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
import redis.asyncio as redis

from backend.judge.config import settings
from backend.jobs.manager import JobManager

# Global instances (initialized in main.py lifespan)
_redis_client: Optional[redis.Redis] = None
_db_session_factory: Optional[sessionmaker] = None
_job_manager: Optional[JobManager] = None

def init_dependencies(redis_client: redis.Redis, database_url: str):
    """Initialize global dependencies - call from main.py lifespan"""
    global _redis_client, _db_session_factory, _job_manager
    
    _redis_client = redis_client
    
    # Create database session factory
    engine = create_engine(database_url)
    _db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize job manager
    _job_manager = JobManager(redis_client, _db_session_factory)
    
    return _job_manager

# Dependency functions
async def get_redis() -> redis.Redis:
    """Get Redis client"""
    if not _redis_client:
        raise RuntimeError("Redis not initialized")
    return _redis_client

def get_db() -> Session:
    """Get database session"""
    if not _db_session_factory:
        raise RuntimeError("Database not initialized")
    
    db = _db_session_factory()
    try:
        yield db
    finally:
        db.close()

async def get_job_manager() -> JobManager:
    """Get job manager instance"""
    if not _job_manager:
        raise RuntimeError("Job manager not initialized")
    return _job_manager