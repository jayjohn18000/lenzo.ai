#!/usr/bin/env python3
"""
Simple database seeding script for NextAGI test users
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

# Database file path
DB_PATH = "nextagi.db"

def create_tables():
    """Create necessary tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            subscription_tier TEXT DEFAULT 'free',
            subscription_status TEXT DEFAULT 'active',
            stripe_customer_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create api_keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT DEFAULT 'Default Key',
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            requests_per_minute INTEGER DEFAULT 60,
            requests_per_day INTEGER DEFAULT 1000,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database tables created/verified")

def seed_test_data():
    """Seed test users and API keys"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Test API key
    test_key = "nextagi_test-key-123"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    
    # Check if test user exists
    cursor.execute("SELECT id FROM users WHERE email = ?", ("test@nextagi.dev",))
    user_result = cursor.fetchone()
    
    if user_result:
        user_id = user_result[0]
        print(f"👤 Test user already exists: test@nextagi.dev (ID: {user_id})")
    else:
        # Create test user
        cursor.execute('''
            INSERT INTO users (email, name, subscription_tier, subscription_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("test@nextagi.dev", "NextAGI Test User", "enterprise", "active", 
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        user_id = cursor.lastrowid
        print(f"👤 Created test user: test@nextagi.dev (ID: {user_id})")
    
    # Check if test API key exists
    cursor.execute("SELECT id FROM api_keys WHERE key_hash = ?", (key_hash,))
    key_result = cursor.fetchone()
    
    if key_result:
        print(f"🔑 Test API key already exists: nextagi_test...")
        # Ensure it's active
        cursor.execute('''
            UPDATE api_keys 
            SET is_active = 1, last_used_at = ?
            WHERE key_hash = ?
        ''', (datetime.utcnow().isoformat(), key_hash))
    else:
        # Create test API key
        cursor.execute('''
            INSERT INTO api_keys (user_id, name, key_hash, key_prefix, is_active, 
                                requests_per_minute, requests_per_day, created_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, "Development Test Key", key_hash, "nextagi_test...", 1,
              1000, 100000, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        print(f"🔑 Created test API key: nextagi_test...")
    
    conn.commit()
    conn.close()
    
    print("✅ Database seeding completed successfully!")
    print("\n📋 Test Credentials:")
    print(f"   API Key: {test_key}")
    print(f"   User: test@nextagi.dev")
    print(f"   Tier: enterprise")
    print(f"   Rate Limits: 1000/min, 100000/day")

if __name__ == "__main__":
    print("🌱 Seeding NextAGI test users and API keys...")
    create_tables()
    seed_test_data()
    print("🎉 Seeding completed!")
