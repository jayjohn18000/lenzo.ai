#!/usr/bin/env python3
"""
Setup script to create a test user and API key for NextAGI authentication.
This bypasses the complex authentication system for development.
"""

import os
import sys
import hashlib
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/Users/jaylenjohnson18/lenzo.ai/lenzo.ai')

def create_test_api_key():
    """Create a simple test API key that works with the current system."""
    
    # The key we want to use
    test_key = "nextagi_test-key-123"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    
    print(f"Creating test API key...")
    print(f"Key: {test_key}")
    print(f"Hash: {key_hash}")
    
    # For now, let's modify the auth system to accept this specific key
    # This is a temporary workaround for development
    
    return test_key, key_hash

def patch_auth_for_development():
    """Temporarily patch the auth system to accept our test key."""
    
    auth_file = '/Users/jaylenjohnson18/lenzo.ai/lenzo.ai/backend/auth/api_key.py'
    
    # Read the current file
    with open(auth_file, 'r') as f:
        content = f.read()
    
    # Find the validate_api_key method and add a bypass for our test key
    if 'async def validate_api_key(self, key: str) -> Dict[str, Any]:' in content:
        # Add a development bypass at the beginning of the method
        new_content = content.replace(
            'async def validate_api_key(self, key: str) -> Dict[str, Any]:\n        """Validate API key and return user/key info"""\n        if not key.startswith("nextagi_"):\n            raise HTTPException(status_code=401, detail="Invalid API key format")',
            '''async def validate_api_key(self, key: str) -> Dict[str, Any]:
        """Validate API key and return user/key info"""
        
        # DEVELOPMENT BYPASS: Accept test key without database lookup
        if key == "nextagi_test-key-123":
            return {
                "user_id": 1,
                "user_email": "test@nextagi.dev",
                "subscription_tier": "enterprise",
                "api_key_id": 1,
                "rate_limits": {
                    "per_minute": 1000,
                    "per_day": 100000,
                },
            }
        
        if not key.startswith("nextagi_"):
            raise HTTPException(status_code=401, detail="Invalid API key format")'''
        )
        
        # Write the modified content back
        with open(auth_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Patched authentication system for development")
        print("✅ Test API key 'nextagi_test-key-123' will now work")
        return True
    
    return False

if __name__ == "__main__":
    print("🔧 Setting up NextAGI test authentication...")
    
    test_key, key_hash = create_test_api_key()
    
    if patch_auth_for_development():
        print("\n🎉 Setup complete!")
        print("You can now use the API with:")
        print("Authorization: Bearer nextagi_test-key-123")
    else:
        print("\n❌ Setup failed - could not patch auth system")
