# backend/middleware/rate_limit.py
import time
from typing import Callable
from fastapi import Request, Response
import redis


class RateLimiter:
    def __init__(self, redis_url: str, limit_per_minute: int = 60):
        self.r = redis.from_url(redis_url, decode_responses=True)
        self.limit = limit_per_minute

    async def __call__(self, request: Request, call_next: Callable):
        # Identify caller by API key (set by auth dependency) or IP fallback
        api_key = request.headers.get("authorization", "")
        key_id = api_key.split()[-1] if api_key else request.client.host
        window = int(time.time() // 60)
        counter_key = f"ratelimit:{key_id}:{window}"
        current = self.r.incr(counter_key)
        if current == 1:
            self.r.expire(counter_key, 65)
        if current > self.limit:
            return Response(status_code=429, content="Rate limit exceeded")
        return await call_next(request)
