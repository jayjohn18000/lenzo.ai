# backend/judge/utils/cache.py
"""
Redis caching utilities for judge pipeline
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
import redis.asyncio as redis
from backend.judge.config import settings

logger = logging.getLogger(__name__)


class JudgeCache:
    """Async Redis cache for judge pipeline results"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.enabled = (
            settings.ENABLE_CACHING if hasattr(settings, "ENABLE_CACHING") else True
        )
        self.default_ttl = 300  # 5 minutes default

    async def connect(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize Redis connection if not provided"""
        if not self.redis and self.enabled:
            try:
                self.redis = redis.Redis(
                    host=host, port=port, db=db, decode_responses=True
                )
                await self.redis.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self.enabled = False

    def _generate_cache_key(
        self,
        prompt: str,
        models: List[str],
        traits: Optional[List[str]] = None,
        mode: str = "balanced",
    ) -> str:
        """Generate deterministic cache key"""
        key_parts = [
            prompt.strip().lower()[:200],  # First 200 chars normalized
            sorted(models),
            sorted(traits) if traits else [],
            mode,
        ]

        key_string = json.dumps(key_parts, sort_keys=True)
        hash_digest = hashlib.md5(key_string.encode()).hexdigest()

        return f"judge:result:{hash_digest}"

    async def get(
        self,
        prompt: str,
        models: List[str],
        traits: Optional[List[str]] = None,
        mode: str = "balanced",
    ) -> Optional[Dict[str, Any]]:
        """Get cached result if available"""
        if not self.enabled or not self.redis:
            return None

        key = self._generate_cache_key(prompt, models, traits, mode)

        try:
            cached_data = await self.redis.get(key)
            if cached_data:
                result = json.loads(cached_data)
                logger.info(f"Cache hit for key: {key[:20]}...")

                # Update metrics
                await self._increment_metric("cache:hits")

                return result
            else:
                await self._increment_metric("cache:misses")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        prompt: str,
        models: List[str],
        result: Dict[str, Any],
        traits: Optional[List[str]] = None,
        mode: str = "balanced",
        ttl: Optional[int] = None,
    ):
        """Cache result with TTL"""
        if not self.enabled or not self.redis:
            return

        key = self._generate_cache_key(prompt, models, traits, mode)
        ttl = ttl or self.default_ttl

        try:
            # Don't cache low confidence results
            if result.get("confidence", 0) < 0.7:
                logger.info("Skipping cache for low confidence result")
                return

            # Don't cache errors
            if result.get("error"):
                return

            cached_data = json.dumps(result)
            await self.redis.setex(key, ttl, cached_data)
            logger.info(f"Cached result for key: {key[:20]}... (TTL: {ttl}s)")

            # Update metrics
            await self._increment_metric("cache:sets")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        if not self.enabled or not self.redis:
            return

        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries")
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def get_metrics(self) -> Dict[str, int]:
        """Get cache performance metrics"""
        if not self.enabled or not self.redis:
            return {}

        try:
            metrics = {}
            for metric in ["cache:hits", "cache:misses", "cache:sets"]:
                value = await self.redis.get(metric)
                metrics[metric] = int(value) if value else 0

            # Calculate hit rate
            total = metrics.get("cache:hits", 0) + metrics.get("cache:misses", 0)
            metrics["hit_rate"] = (
                metrics.get("cache:hits", 0) / total if total > 0 else 0
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}

    async def _increment_metric(self, metric_key: str):
        """Increment a metric counter"""
        try:
            await self.redis.incr(metric_key)
        except:
            pass  # Ignore metric errors

    async def warmup(self, common_queries: List[Dict[str, Any]]):
        """Pre-warm cache with common queries"""
        if not self.enabled:
            return

        logger.info(f"Warming up cache with {len(common_queries)} queries")

        for query_data in common_queries:
            # Check if already cached
            existing = await self.get(
                query_data["prompt"],
                query_data["models"],
                query_data.get("traits"),
                query_data.get("mode", "balanced"),
            )

            if not existing and "result" in query_data:
                # Cache the pre-computed result
                await self.set(
                    query_data["prompt"],
                    query_data["models"],
                    query_data["result"],
                    query_data.get("traits"),
                    query_data.get("mode", "balanced"),
                    ttl=3600,  # 1 hour for warmed entries
                )

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()


# Global cache instance
_cache_instance: Optional[JudgeCache] = None


async def get_cache() -> JudgeCache:
    """Get or create global cache instance"""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = JudgeCache()
        await _cache_instance.connect(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            db=getattr(settings, "REDIS_CACHE_DB", 1),
        )

    return _cache_instance


# Decorator for automatic caching
from functools import wraps


def cached_result(ttl: int = 300):
    """Decorator to cache judge pipeline results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(req, trace_id, *args, **kwargs):
            cache = await get_cache()

            # Try to get from cache
            cached = await cache.get(
                req.prompt,
                req.options.models or [],
                req.expected_traits,
                req.options.model_selection_mode,
            )

            if cached:
                logger.info(f"[{trace_id}] Returning cached result")
                cached["from_cache"] = True
                cached["trace_id"] = trace_id  # Update trace ID
                return cached

            # Execute function
            result = await func(req, trace_id, *args, **kwargs)

            # Cache the result
            await cache.set(
                req.prompt,
                result.get("models_attempted", []),
                result,
                req.expected_traits,
                req.options.model_selection_mode,
                ttl=ttl,
            )

            return result

        return wrapper

    return decorator
