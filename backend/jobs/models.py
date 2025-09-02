# backend/jobs/models.py
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class QueryJob(Base):
    __tablename__ = "query_jobs"
    
    id = Column(String(36), primary_key=True)  # UUID
    status = Column(String(20), default=JobStatus.PENDING)
    prompt = Column(Text, nullable=False)
    request_params = Column(JSON)  # Store full request params
    
    # Results
    result = Column(JSON)  # Store full QueryResponse
    error = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Performance tracking
    estimated_time_ms = Column(Float)
    actual_time_ms = Column(Float)