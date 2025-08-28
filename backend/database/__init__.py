# backend/database/__init__.py
from contextlib import contextmanager
from .models import init_db, get_session, QueryRequest, ModelResponse

_engine = None

def get_db_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        _engine = init_db()
    return _engine

@contextmanager
def get_db():
    """Database session context manager"""
    engine = get_db_engine()
    session = get_session(engine)
    try:
        yield session
    finally:
        session.close()