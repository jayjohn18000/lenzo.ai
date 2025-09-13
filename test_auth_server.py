#!/usr/bin/env python3
"""
Simple test server to verify authentication is working
"""

import os
import sys
import asyncio
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add current directory to path
sys.path.append('.')

# Import our authentication
from backend.auth.api_key import verify_api_key

app = FastAPI(title="NextAGI Auth Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "NextAGI Auth Test Server", "status": "running"}

@app.get("/auth/test")
async def test_auth(current_key: dict = Security(verify_api_key)):
    """Test authentication endpoint"""
    return {
        "status": "authenticated",
        "user_id": current_key.get("user_id"),
        "user_email": current_key.get("user_email"),
        "subscription_tier": current_key.get("subscription_tier"),
        "auth_method": current_key.get("auth_method", "unknown"),
        "timestamp": current_key.get("timestamp"),
        "message": "Authentication successful"
    }

@app.post("/api/v1/query")
async def test_query(
    request: dict,
    current_key: dict = Security(verify_api_key)
):
    """Test query endpoint - returns sync response"""
    return {
        "request_id": "test-123",
        "answer": "This is a test response from the authentication test server",
        "confidence": 0.95,
        "winner_model": "test-model",
        "response_time_ms": 100,
        "models_used": ["test-model"],
        "auth_method": current_key.get("auth_method", "unknown"),
        "status": "success",
        "message": "Query processed successfully with authentication"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "server": "auth-test"}

if __name__ == "__main__":
    print("🚀 Starting NextAGI Auth Test Server...")
    print("📋 Test API Key: nextagi_test-key-123")
    print("🔗 Test URL: http://localhost:8000/auth/test")
    print("🔗 Query URL: http://localhost:8000/api/v1/query")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
