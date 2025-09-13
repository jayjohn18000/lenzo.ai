#!/usr/bin/env python3
"""
NextAGI Test User Seeding Script
Creates test users and API keys for development and testing
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.auth.api_key import User, APIKey, PRICING_TIERS
from backend.judge.config import settings


def create_test_users(session) -> List[Dict[str, Any]]:
    """Create test users with different subscription tiers"""
    
    test_users = [
        {
            "email": "dev@nextagi.local",
            "subscription_tier": "enterprise",
            "subscription_status": "active",
            "name": "Development User",
            "api_keys": [
                {
                    "name": "Test API Key",
                    "key": "nextagi_test-key-123",
                    "requests_per_minute": 1000,
                    "requests_per_day": 100000,
                }
            ]
        },
        {
            "email": "free@nextagi.local", 
            "subscription_tier": "free",
            "subscription_status": "active",
            "name": "Free Tier User",
            "api_keys": [
                {
                    "name": "Free Tier Key",
                    "key": "nextagi_free-key-456",
                    "requests_per_minute": 5,
                    "requests_per_day": 100,
                }
            ]
        },
        {
            "email": "starter@nextagi.local",
            "subscription_tier": "starter", 
            "subscription_status": "active",
            "name": "Starter Tier User",
            "api_keys": [
                {
                    "name": "Starter Key",
                    "key": "nextagi_starter-key-789",
                    "requests_per_minute": 60,
                    "requests_per_day": 1000,
                }
            ]
        },
        {
            "email": "pro@nextagi.local",
            "subscription_tier": "professional",
            "subscription_status": "active", 
            "name": "Professional User",
            "api_keys": [
                {
                    "name": "Pro Key",
                    "key": "nextagi_pro-key-101",
                    "requests_per_minute": 300,
                    "requests_per_day": 10000,
                }
            ]
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Check if user already exists
        existing_user = session.query(User).filter(User.email == user_data["email"]).first()
        
        if existing_user:
            print(f"✅ User {user_data['email']} already exists")
            created_users.append({
                "user": existing_user,
                "api_keys": existing_user.api_keys
            })
            continue
            
        # Create new user
        user = User(
            email=user_data["email"],
            subscription_tier=user_data["subscription_tier"],
            subscription_status=user_data["subscription_status"],
            name=user_data["name"],
            created_at=datetime.utcnow()
        )
        
        session.add(user)
        session.flush()  # Get the user ID
        
        # Create API keys for this user
        created_api_keys = []
        for key_data in user_data["api_keys"]:
            key_hash = hashlib.sha256(key_data["key"].encode()).hexdigest()
            key_prefix = key_data["key"][:12] + "..."
            
            # Check if API key already exists
            existing_key = session.query(APIKey).filter(APIKey.key_hash == key_hash).first()
            if existing_key:
                print(f"  ✅ API key {key_data['name']} already exists")
                created_api_keys.append(existing_key)
                continue
            
            api_key = APIKey(
                user_id=user.id,
                name=key_data["name"],
                key_hash=key_hash,
                key_prefix=key_prefix,
                is_active=True,
                requests_per_minute=key_data["requests_per_minute"],
                requests_per_day=key_data["requests_per_day"],
                created_at=datetime.utcnow()
            )
            
            session.add(api_key)
            created_api_keys.append(api_key)
            
        session.commit()
        
        created_users.append({
            "user": user,
            "api_keys": created_api_keys
        })
        
        print(f"✅ Created user {user_data['email']} with {len(created_api_keys)} API key(s)")
    
    return created_users


def print_api_key_summary(created_users: List[Dict[str, Any]]):
    """Print a summary of created API keys"""
    
    print("\n" + "="*60)
    print("🔑 API KEY SUMMARY")
    print("="*60)
    
    for user_data in created_users:
        user = user_data["user"]
        print(f"\n👤 User: {user.email}")
        print(f"   Tier: {user.subscription_tier}")
        print(f"   Status: {user.subscription_status}")
        
        for api_key in user_data["api_keys"]:
            # Find the original key from our test data
            original_key = None
            if api_key.key_prefix == "nextagi_test...":
                original_key = "nextagi_test-key-123"
            elif api_key.key_prefix == "nextagi_free...":
                original_key = "nextagi_free-key-456" 
            elif api_key.key_prefix == "nextagi_starter...":
                original_key = "nextagi_starter-key-789"
            elif api_key.key_prefix == "nextagi_pro...":
                original_key = "nextagi_pro-key-101"
                
            if original_key:
                print(f"   🔑 API Key: {original_key}")
                print(f"      Rate Limit: {api_key.requests_per_minute}/min, {api_key.requests_per_day}/day")
    
    print("\n" + "="*60)
    print("📋 USAGE EXAMPLES")
    print("="*60)
    print("Test the API with any of these keys:")
    print("")
    print("# Development key (unlimited)")
    print('curl -X POST http://localhost:8000/api/v1/query \\')
    print('  -H "Authorization: Bearer nextagi_test-key-123" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"prompt": "Hello, world!", "mode": "balanced"}\'')
    print("")
    print("# Free tier key (5/min, 100/day)")
    print('curl -X POST http://localhost:8000/api/v1/query \\')
    print('  -H "Authorization: Bearer nextagi_free-key-456" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"prompt": "Hello, world!", "mode": "balanced"}\'')
    print("")
    print("="*60)


def main():
    """Main seeding function"""
    
    print("🌱 NextAGI Test User Seeding Script")
    print("===================================")
    
    try:
        # Create database connection
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables if they don't exist
        from backend.auth.api_key import Base as AuthBase
        AuthBase.metadata.create_all(bind=engine)
        
        # Create session
        session = SessionLocal()
        
        try:
            # Create test users
            created_users = create_test_users(session)
            
            # Print summary
            print_api_key_summary(created_users)
            
            print(f"\n🎉 Successfully seeded {len(created_users)} test users!")
            print("✅ Database is ready for development and testing")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error seeding test users: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
