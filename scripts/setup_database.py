# scripts/setup_database.py
"""
Database setup and migration script for NextAGI.
Creates all necessary tables and indexes for production deployment.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import hashlib
import secrets

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.auth.api_key import Base, User, APIKey, UsageRecord
from backend.judge.config import settings


def create_database():
    """Create database and all tables"""
    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

    # Create indexes for performance
    with engine.connect() as conn:
        # Indexes for frequently queried columns
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_user_id ON usage_records(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_timestamp ON usage_records(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_api_key_id ON usage_records(api_key_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON users(subscription_tier);",
        ]

        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                print(f"✅ Index created: {index_sql.split()[5]}")
            except Exception as e:
                print(f"⚠️  Index might already exist: {e}")

        conn.commit()


def create_admin_user():
    """Create initial admin user and API key"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.email == "admin@nextagi.com").first()

        if not admin_user:
            # Create admin user
            admin_user = User(
                email="admin@nextagi.com",
                name="NextAGI Admin",
                subscription_tier="enterprise",
                subscription_status="active",
                created_at=datetime.utcnow(),
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("✅ Admin user created")
        else:
            print("ℹ️  Admin user already exists")

        # Create API key for admin
        existing_key = db.query(APIKey).filter(APIKey.user_id == admin_user.id).first()

        if not existing_key:
            # Generate API key
            key = f"nextagi_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(key.encode()).hexdigest()

            api_key = APIKey(
                user_id=admin_user.id,
                name="Admin Key",
                key_hash=key_hash,
                key_prefix=key[:12] + "...",
                requests_per_minute=1000,
                requests_per_day=100000,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(api_key)
            db.commit()

            print(f"✅ Admin API key created: {key}")
            print(f"   Save this key securely - it won't be shown again!")
        else:
            print("ℹ️  Admin API key already exists")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def create_demo_data():
    """Create demo users and usage data for testing"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    demo_users = [
        {"email": "demo@example.com", "name": "Demo User", "tier": "starter"},
        {
            "email": "enterprise@example.com",
            "name": "Enterprise User",
            "tier": "enterprise",
        },
    ]

    try:
        for user_data in demo_users:
            # Check if user exists
            existing_user = (
                db.query(User).filter(User.email == user_data["email"]).first()
            )

            if not existing_user:
                # Create user
                user = User(
                    email=user_data["email"],
                    name=user_data["name"],
                    subscription_tier=user_data["tier"],
                    subscription_status="active",
                    created_at=datetime.utcnow(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Create API key
                key = f"nextagi_{secrets.token_urlsafe(32)}"
                key_hash = hashlib.sha256(key.encode()).hexdigest()

                api_key = APIKey(
                    user_id=user.id,
                    name="Demo Key",
                    key_hash=key_hash,
                    key_prefix=key[:12] + "...",
                    requests_per_minute=60 if user_data["tier"] == "starter" else 300,
                    requests_per_day=1000 if user_data["tier"] == "starter" else 10000,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.add(api_key)
                db.commit()
                db.refresh(api_key)

                # Create some demo usage records
                for i in range(50):
                    usage_record = UsageRecord(
                        user_id=user.id,
                        api_key_id=api_key.id,
                        request_id=f"demo_{secrets.token_hex(8)}",
                        total_tokens=500 + (i * 10),
                        models_attempted='["openai/gpt-4", "anthropic/claude-3.5-sonnet"]',
                        models_succeeded='["openai/gpt-4", "anthropic/claude-3.5-sonnet"]',
                        winner_model=(
                            "openai/gpt-4"
                            if i % 2 == 0
                            else "anthropic/claude-3.5-sonnet"
                        ),
                        response_time_ms=2000 + (i * 50),
                        confidence_score=0.8 + (i % 20) * 0.01,
                        estimated_cost=0.02 + (i * 0.001),
                        timestamp=datetime.utcnow() - timedelta(days=i // 2),
                    )
                    db.add(usage_record)

                db.commit()
                print(f"✅ Demo user created: {user_data['email']} with API key: {key}")
            else:
                print(f"ℹ️  Demo user already exists: {user_data['email']}")

    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        db.rollback()
    finally:
        db.close()


def verify_setup():
    """Verify that the database setup is working correctly"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Test queries
        user_count = db.query(User).count()
        api_key_count = db.query(APIKey).count()
        usage_count = db.query(UsageRecord).count()

        print(f"\n📊 Database Verification:")
        print(f"   Users: {user_count}")
        print(f"   API Keys: {api_key_count}")
        print(f"   Usage Records: {usage_count}")

        # Test a complex query
        recent_usage = (
            db.query(UsageRecord)
            .filter(UsageRecord.timestamp >= datetime.utcnow() - timedelta(days=7))
            .count()
        )
        print(f"   Recent Usage (7 days): {recent_usage}")

        print("✅ Database verification completed successfully")
        return True

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Setting up NextAGI Database...")
    print(f"Database URL: {settings.DATABASE_URL}")

    # Create database and tables
    create_database()

    # Create admin user
    create_admin_user()

    # Create demo data
    if input("\nCreate demo data? (y/N): ").lower() == "y":
        create_demo_data()

    # Verify setup
    if verify_setup():
        print("\n🎉 Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the FastAPI server: uvicorn backend.main:app --reload")
        print("2. Test the API endpoints with your API key")
        print("3. Set up your frontend environment")
    else:
        print("\n❌ Setup verification failed. Please check the errors above.")
        sys.exit(1)
