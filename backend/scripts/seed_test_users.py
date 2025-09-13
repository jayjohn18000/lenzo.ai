#!/usr/bin/env python3
"""
Database seeding script for NextAGI test users and API keys.
This creates a robust test environment with proper user management.
"""

import os
import sys
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, create_tables
from backend.auth.api_key import User, APIKey, APIKeyManager, PRICING_TIERS
import hashlib


async def seed_test_users():
    """Create test users and API keys for development"""
    print("🌱 Seeding NextAGI test users and API keys...")
    
    # Create tables if they don't exist
    create_tables()
    print("✅ Database tables created/verified")
    
    with get_db() as db:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.email == "test@nextagi.dev").first()
        
        if existing_user:
            print(f"👤 Test user already exists: {existing_user.email}")
            user_id = existing_user.id
        else:
            # Create test user
            test_user = User(
                email="test@nextagi.dev",
                name="NextAGI Test User",
                subscription_tier="enterprise",
                subscription_status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            user_id = test_user.id
            print(f"👤 Created test user: {test_user.email} (ID: {user_id})")
        
        # Check if test API key already exists
        test_key = "nextagi_test-key-123"
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        
        existing_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
        
        if existing_key:
            print(f"🔑 Test API key already exists: {existing_key.key_prefix}")
            # Ensure it's active
            existing_key.is_active = True
            existing_key.last_used_at = datetime.utcnow()
            db.commit()
        else:
            # Create test API key
            api_key = APIKey(
                user_id=user_id,
                name="Development Test Key",
                key_hash=key_hash,
                key_prefix="nextagi_test...",
                is_active=True,
                requests_per_minute=1000,
                requests_per_day=100000,
                created_at=datetime.utcnow(),
                last_used_at=datetime.utcnow()
            )
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            print(f"🔑 Created test API key: {api_key.key_prefix}")
        
        # Create additional test users for different tiers
        test_users = [
            {
                "email": "starter@nextagi.dev",
                "name": "Starter Test User",
                "tier": "starter"
            },
            {
                "email": "professional@nextagi.dev", 
                "name": "Professional Test User",
                "tier": "professional"
            },
            {
                "email": "free@nextagi.dev",
                "name": "Free Test User", 
                "tier": "free"
            }
        ]
        
        for user_data in test_users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    email=user_data["email"],
                    name=user_data["name"],
                    subscription_tier=user_data["tier"],
                    subscription_status="active",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"👤 Created {user_data['tier']} user: {user.email}")
        
        print("✅ Database seeding completed successfully!")
        print("\n📋 Test Credentials:")
        print(f"   API Key: {test_key}")
        print(f"   User: test@nextagi.dev")
        print(f"   Tier: enterprise")
        print(f"   Rate Limits: 1000/min, 100000/day")


if __name__ == "__main__":
    asyncio.run(seed_test_users())
