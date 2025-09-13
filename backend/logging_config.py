# backend/logging_config.py
"""Database logging configuration for NextAGI."""

import logging
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.database.models import QueryRequest, ModelResponse


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to database."""
    
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
    
    def emit(self, record):
        """Write log record to database."""
        try:
            # Only log important events to database (not debug/info spam)
            if record.levelno >= logging.WARNING:
                self._write_to_db(record)
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Database logging error: {e}")
    
    def _write_to_db(self, record):
        """Write a single log record to database."""
        # This is a simple implementation - you could expand this
        # to create a dedicated log_entries table if needed
        pass


class QueryLogger:
    """Logger for query-specific events."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def log_query_request(self, request_id: str, prompt: str, mode: str, max_models: int):
        """Log a query request to the database."""
        try:
            with self.session_factory() as session:
                query_request = QueryRequest(
                    request_id=request_id,
                    prompt=prompt[:500],  # Truncate long prompts
                    mode=mode,
                    max_models=max_models,
                    created_at=datetime.utcnow()
                )
                session.add(query_request)
                session.commit()
        except Exception as e:
            print(f"Failed to log query request: {e}")
    
    def log_query_response(self, request_id: str, response_data: dict):
        """Log query response data to database."""
        try:
            with self.session_factory() as session:
                # Update the query request with response data
                query_request = session.query(QueryRequest).filter_by(
                    request_id=request_id
                ).first()
                
                if query_request:
                    query_request.response_time_ms = response_data.get('response_time_ms')
                    query_request.total_cost = response_data.get('total_cost')
                    query_request.winner_confidence = response_data.get('confidence')
                    query_request.winner_model = response_data.get('winner_model')
                    query_request.models_used = response_data.get('models_used', [])
                    
                    session.commit()
                    
                    # Log individual model responses
                    for metric in response_data.get('model_metrics', []):
                        model_response = ModelResponse(
                            request_id=request_id,
                            model_name=metric.get('model'),
                            response_text=metric.get('response', '')[:1000],  # Truncate
                            confidence_score=metric.get('confidence'),
                            response_time_ms=metric.get('response_time_ms'),
                            cost=metric.get('cost'),
                            reliability_score=metric.get('reliability_score'),
                            consistency_score=metric.get('consistency_score'),
                            hallucination_risk=metric.get('hallucination_risk'),
                            citation_quality=metric.get('citation_quality'),
                            rank_position=metric.get('rank_position'),
                            is_winner=metric.get('is_winner', False),
                            error_message=metric.get('error'),
                            trait_scores=metric.get('trait_scores', {})
                        )
                        session.add(model_response)
                    
                    session.commit()
        except Exception as e:
            print(f"Failed to log query response: {e}")


def setup_database_logging(session_factory):
    """Set up database logging configuration."""
    
    # Create query logger instance
    query_logger = QueryLogger(session_factory)
    
    # Add database handler to root logger for warnings and errors
    db_handler = DatabaseLogHandler(session_factory)
    db_handler.setLevel(logging.WARNING)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(db_handler)
    
    return query_logger
