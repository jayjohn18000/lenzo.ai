"""
Authentication health checks and monitoring for NextAGI
"""

import os
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth.api_key import APIKeyManager, User, APIKey
import redis
import logging

logger = logging.getLogger(__name__)


class AuthHealthChecker:
    """Comprehensive authentication system health monitoring"""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection for rate limiting checks"""
        try:
            self.redis_client = redis.Redis(
                host="localhost", 
                port=6379, 
                db=0, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations"""
        try:
            with get_db() as db:
                # Test basic query
                user_count = db.query(User).count()
                api_key_count = db.query(APIKey).count()
                
                return {
                    "status": "healthy",
                    "user_count": user_count,
                    "api_key_count": api_key_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_redis_connectivity(self) -> Dict[str, Any]:
        """Check Redis connectivity for rate limiting"""
        if not self.redis_client:
            return {
                "status": "unhealthy",
                "error": "Redis client not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Test Redis operations
            test_key = f"health_check:{int(time.time())}"
            self.redis_client.set(test_key, "test", ex=10)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if value == "test":
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Redis read/write test failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_test_api_key(self) -> Dict[str, Any]:
        """Verify test API key exists and is active"""
        try:
            with get_db() as db:
                test_key = "nextagi_test-key-123"
                key_hash = hashlib.sha256(test_key.encode()).hexdigest()
                
                api_key = db.query(APIKey).filter(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                ).first()
                
                if api_key:
                    return {
                        "status": "healthy",
                        "key_prefix": api_key.key_prefix,
                        "user_id": api_key.user_id,
                        "rate_limits": {
                            "per_minute": api_key.requests_per_minute,
                            "per_day": api_key.requests_per_day
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": "Test API key not found or inactive",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Test API key check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all authentication health checks"""
        results = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Database check
        db_result = await self.check_database_connectivity()
        results["checks"]["database"] = db_result
        if db_result["status"] != "healthy":
            results["overall_status"] = "unhealthy"
        
        # Redis check
        redis_result = await self.check_redis_connectivity()
        results["checks"]["redis"] = redis_result
        if redis_result["status"] != "healthy":
            results["overall_status"] = "degraded"  # Redis is optional for basic auth
        
        # Test API key check
        key_result = await self.check_test_api_key()
        results["checks"]["test_api_key"] = key_result
        if key_result["status"] != "healthy":
            results["overall_status"] = "unhealthy"
        
        return results


# Global health checker instance
auth_health_checker = AuthHealthChecker()


async def get_auth_health() -> Dict[str, Any]:
    """Get comprehensive authentication health status"""
    return await auth_health_checker.comprehensive_health_check()
