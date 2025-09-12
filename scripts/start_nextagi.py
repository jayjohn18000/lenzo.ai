#!/usr/bin/env python3
"""
NextAGI startup script with debugging and validation
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")

    # Check if .env file exists
    if not Path(".env").exists():
        print("❌ .env file not found!")
        print("📝 Please copy .env.example to .env and configure your API keys")
        return False

    # Check if API key is configured
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "your-openrouter-key-here":
        print("❌ OPENROUTER_API_KEY not configured!")
        print("📝 Please set your OpenRouter API key in .env file")
        return False

    print("✅ Requirements check passed")
    return True


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
        )
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def test_api():
    """Test if the API is responding"""
    print("🧪 Testing API...")

    import httpx
    import asyncio

    async def test():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ API is healthy: {data.get('status')}")
                    print(f"📊 Available models: {data.get('available_models', 0)}")
                    return True
                else:
                    print(f"❌ API health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

    return asyncio.run(test())


def start_development_server():
    """Start the development server"""
    print("🚀 Starting NextAGI development server...")

    try:
        # Start backend
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        subprocess.run(
            [
                "uvicorn",
                "backend.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
                "--log-level",
                "info",
            ],
            env=env,
            check=True,
        )

    except KeyboardInterrupt:
        print("\n👋 Shutting down NextAGI...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")


def main():
    """Main startup routine"""
    print("🎯 NextAGI Startup Script")
    print("=" * 40)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Start server
    start_development_server()


if __name__ == "__main__":
    main()
