# backend/auth/api_key.py
"""
API Key authentication and usage tracking system for NextAGI monetization.
Supports tiered pricing, rate limiting, and comprehensive usage analytics.
"""

import secrets
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from backend.database import get_db
import redis
import json

# Database Models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    subscription_tier = Column(
        String, default="free"
    )  # free, starter, professional, enterprise
    subscription_status = Column(
        String, default="active"
    )  # active, cancelled, past_due
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user")
    usage_records = relationship("UsageRecord", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String, default="Default Key")
    key_hash = Column(String, unique=True, index=True)
    key_prefix = Column(String, index=True)  # First 8 chars for display
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # Rate limiting
    requests_per_minute = Column(Integer, default=60)
    requests_per_day = Column(Integer, default=1000)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    api_key_id = Column(Integer, index=True)
    request_id = Column(String, index=True)

    # Request details
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Models used
    models_attempted = Column(Text)  # JSON string
    models_succeeded = Column(Text)  # JSON string
    winner_model = Column(String)

    # Performance metrics
    response_time_ms = Column(Integer)
    confidence_score = Column(Float)

    # Costs
    estimated_cost = Column(Float, default=0.0)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_records")


# Pricing Configuration
PRICING_TIERS = {
    "free": {
        "monthly_requests": 100,
        "rate_limit_per_minute": 5,
        "rate_limit_per_day": 100,
        "price_per_request": 0.0,
        "features": ["basic_routing", "single_model"],
    },
    "starter": {
        "monthly_requests": 5000,
        "rate_limit_per_minute": 60,
        "rate_limit_per_day": 1000,
        "price_per_request": 0.01,
        "features": ["advanced_routing", "multi_model", "analytics"],
    },
    "professional": {
        "monthly_requests": 50000,
        "rate_limit_per_minute": 300,
        "rate_limit_per_day": 10000,
        "price_per_request": 0.008,
        "features": [
            "advanced_routing",
            "multi_model",
            "analytics",
            "custom_models",
            "priority_support",
        ],
    },
    "enterprise": {
        "monthly_requests": 500000,
        "rate_limit_per_minute": 1000,
        "rate_limit_per_day": 100000,
        "price_per_request": 0.005,
        "features": [
            "all_features",
            "white_label",
            "dedicated_support",
            "custom_deployment",
        ],
    },
}

# Redis for rate limiting
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

security = HTTPBearer()


class APIKeyManager:
    """Manages API key generation, validation, and usage tracking"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_api_key(
        self, user_id: int, name: str = "Default Key"
    ) -> Dict[str, Any]:
        """Generate new API key for user"""
        # Generate secure key
        key = f"nextagi_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_prefix = key[:12] + "..."

        # Get user to set appropriate rate limits
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        tier_config = PRICING_TIERS.get(user.subscription_tier, PRICING_TIERS["free"])

        # Create API key record
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            requests_per_minute=tier_config["rate_limit_per_minute"],
            requests_per_day=tier_config["rate_limit_per_day"],
            is_active=True,
            created_at=datetime.utcnow(),
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return {
            "api_key": key,  # Only returned once
            "key_id": api_key.id,
            "name": name,
            "prefix": key_prefix,
            "rate_limits": {
                "per_minute": api_key.requests_per_minute,
                "per_day": api_key.requests_per_day,
            },
        }

    async def validate_api_key(self, key: str) -> Dict[str, Any]:
        """Validate API key and return user/key info"""
        if not key.startswith("nextagi_"):
            raise HTTPException(status_code=401, detail="Invalid API key format")

        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # Query database
        api_key = (
            self.db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
            .first()
        )

        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid or inactive API key")

        # Get user
        user = self.db.query(User).filter(User.id == api_key.user_id).first()
        if not user or user.subscription_status != "active":
            raise HTTPException(status_code=401, detail="User account inactive")

        # Update last used
        api_key.last_used_at = datetime.utcnow()
        self.db.commit()

        return {
            "user_id": user.id,
            "user_email": user.email,
            "subscription_tier": user.subscription_tier,
            "api_key_id": api_key.id,
            "rate_limits": {
                "per_minute": api_key.requests_per_minute,
                "per_day": api_key.requests_per_day,
            },
        }

    async def check_rate_limits(self, user_id: int, api_key_id: int) -> bool:
        """Check if user has exceeded rate limits"""
        # Get rate limits
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key:
            return False

        current_time = int(time.time())

        # Check per-minute limit
        minute_key = f"rate_limit:minute:{user_id}:{current_time // 60}"
        minute_count = redis_client.get(minute_key)
        if minute_count and int(minute_count) >= api_key.requests_per_minute:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded: requests per minute"
            )

        # Check per-day limit
        day_key = f"rate_limit:day:{user_id}:{current_time // 86400}"
        day_count = redis_client.get(day_key)
        if day_count and int(day_count) >= api_key.requests_per_day:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded: requests per day"
            )

        return True

    async def increment_rate_limits(self, user_id: int):
        """Increment rate limit counters"""
        current_time = int(time.time())

        # Increment minute counter
        minute_key = f"rate_limit:minute:{user_id}:{current_time // 60}"
        pipe = redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)

        # Increment day counter
        day_key = f"rate_limit:day:{user_id}:{current_time // 86400}"
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)

        pipe.execute()

    async def track_usage(
        self,
        user_id: int,
        api_key_id: int,
        request_id: str,
        models_attempted: List[str],
        models_succeeded: List[str],
        winner_model: str,
        total_tokens: int,
        response_time_ms: int,
        confidence_score: float,
    ) -> UsageRecord:
        """Track usage for billing and analytics"""

        # Calculate estimated cost
        estimated_cost = self._calculate_cost(
            user_id, total_tokens, len(models_attempted)
        )

        usage_record = UsageRecord(
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            total_tokens=total_tokens,
            models_attempted=json.dumps(models_attempted),
            models_succeeded=json.dumps(models_succeeded),
            winner_model=winner_model,
            response_time_ms=response_time_ms,
            confidence_score=confidence_score,
            estimated_cost=estimated_cost,
            timestamp=datetime.utcnow(),
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record

    def _calculate_cost(self, user_id: int, tokens: int, models_count: int) -> float:
        """Calculate estimated cost based on tokens and models used"""
        user = self.db.query(User).filter(User.id == user_id).first()
        tier_config = PRICING_TIERS.get(user.subscription_tier, PRICING_TIERS["free"])

        # Base cost per request
        base_cost = tier_config["price_per_request"]

        # Additional cost for tokens (rough estimate)
        token_cost = (tokens / 1000) * 0.002  # $0.002 per 1K tokens

        # Additional cost for multiple models
        model_multiplier = 1 + (models_count - 1) * 0.1

        return (base_cost + token_cost) * model_multiplier

    async def get_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for user dashboard"""
        since_date = datetime.utcnow() - timedelta(days=days)

        # Query usage records
        usage_records = (
            self.db.query(UsageRecord)
            .filter(UsageRecord.user_id == user_id, UsageRecord.timestamp >= since_date)
            .all()
        )

        if not usage_records:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0,
                "avg_confidence": 0.0,
                "top_models": [],
                "daily_usage": [],
            }

        # Calculate statistics
        total_requests = len(usage_records)
        total_tokens = sum(r.total_tokens for r in usage_records)
        total_cost = sum(r.estimated_cost for r in usage_records)
        avg_response_time = (
            sum(r.response_time_ms for r in usage_records) / total_requests
        )
        avg_confidence = sum(r.confidence_score for r in usage_records) / total_requests

        # Top models
        model_counts = {}
        for record in usage_records:
            if record.winner_model:
                model_counts[record.winner_model] = (
                    model_counts.get(record.winner_model, 0) + 1
                )

        top_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Daily usage breakdown
        daily_usage = {}
        for record in usage_records:
            day = record.timestamp.date()
            if day not in daily_usage:
                daily_usage[day] = {"requests": 0, "tokens": 0, "cost": 0.0}
            daily_usage[day]["requests"] += 1
            daily_usage[day]["tokens"] += record.total_tokens
            daily_usage[day]["cost"] += record.estimated_cost

        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_response_time": round(avg_response_time, 2),
            "avg_confidence": round(avg_confidence, 3),
            "top_models": top_models,
            "daily_usage": [
                {"date": str(date), **stats}
                for date, stats in sorted(daily_usage.items())
            ],
        }


# FastAPI Dependencies
async def verify_api_key(token: str = Security(security)) -> Dict[str, Any]:
    """FastAPI dependency for API key verification"""
    db = next(get_db())
    api_manager = APIKeyManager(db)

    # Validate key
    key_info = await api_manager.validate_api_key(token.credentials)

    # Check rate limits
    await api_manager.check_rate_limits(key_info["user_id"], key_info["api_key_id"])

    # Increment counters
    await api_manager.increment_rate_limits(key_info["user_id"])

    return key_info


async def get_api_manager(db: Session = Depends(get_db)) -> APIKeyManager:
    """FastAPI dependency for API manager"""
    return APIKeyManager(db)
