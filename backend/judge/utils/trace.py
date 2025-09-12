# backend/judge/utils/trace.py
"""
Tracing utilities for request tracking and observability
"""

import uuid
from typing import Optional
import time


def new_trace_id() -> str:
    """Generate a new unique trace ID for request tracking"""
    return str(uuid.uuid4())


def format_trace_log(trace_id: str, message: str, **kwargs) -> str:
    """Format a log message with trace ID and optional metadata"""
    timestamp = time.time()
    extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
    return f"[{trace_id}] {timestamp} {message} {extra_info}".strip()
