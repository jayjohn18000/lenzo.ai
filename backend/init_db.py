# backend/init_db.py (Initialize database script)
"""
Initialize database with all tables
Run this script to set up your database: python -m backend.init_db
"""

from backend.database import engine
from backend.models.query_history import Base


def init_database():
    """Create all tables in the database"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    init_database()
