# backend/database/models.py
"""SQLite database models for NextAGI"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class QueryRequest(Base):
    """Store each query request for analytics"""
    __tablename__ = "query_requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), unique=True, index=True)
    prompt = Column(Text, nullable=False)
    mode = Column(String(20))  # speed, quality, balanced, cost
    max_models = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Integer)
    total_tokens_used = Column(Integer)
    total_cost = Column(Float)
    winner_confidence = Column(Float)
    winner_model = Column(String(100))
    models_used_json = Column(Text)  # JSON array of model names
    
    # Relationships
    model_responses = relationship("ModelResponse", back_populates="query_request", cascade="all, delete-orphan")
    
    @property
    def models_used(self):
        return json.loads(self.models_used_json) if self.models_used_json else []
    
    @models_used.setter
    def models_used(self, value):
        self.models_used_json = json.dumps(value)

class ModelResponse(Base):
    """Store individual model responses for analysis"""
    __tablename__ = "model_responses"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), ForeignKey("query_requests.request_id"))
    model_name = Column(String(100))
    response_text = Column(Text)
    confidence_score = Column(Float)  # Must be 0-1
    response_time_ms = Column(Integer)
    tokens_used = Column(Integer)
    cost = Column(Float)
    reliability_score = Column(Float)
    consistency_score = Column(Float)
    hallucination_risk = Column(Float)
    citation_quality = Column(Float)
    rank_position = Column(Integer)
    is_winner = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store trait scores as JSON
    trait_scores_json = Column(Text)
    
    # Relationship
    query_request = relationship("QueryRequest", back_populates="model_responses")
    
    @property
    def trait_scores(self):
        return json.loads(self.trait_scores_json) if self.trait_scores_json else {}
    
    @trait_scores.setter
    def trait_scores(self, value):
        self.trait_scores_json = json.dumps(value)

# Database initialization
def init_db(database_url: str = "sqlite:///nextagi.db"):
    """Initialize the database with tables"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

# Session factory
def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()

