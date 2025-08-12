# backend/judge/utils/trace.py
import time
import os
import random
import string

def new_trace_id(prefix: str = "tr") -> str:
    """
    Compact, sortable-ish trace id: tr_<millis>_<6 random>
    Example: tr_1733762512345_k9q2fz
    """
    ts = int(time.time() * 1000)
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{ts}_{rand}"
