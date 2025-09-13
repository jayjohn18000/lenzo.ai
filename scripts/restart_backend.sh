#!/bin/bash

# NextAGI Backend Restart Script
# Ensures proper environment setup and configuration persistence

set -e  # Exit on any error

echo "🚀 NextAGI Backend Restart Script"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Starting NextAGI backend restart process..."

# 1. Kill any existing backend processes
print_status "Stopping existing backend processes..."
pkill -f "uvicorn.*backend.main:app" || print_warning "No existing backend processes found"
sleep 2

# 2. Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Please create it first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 3. Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# 4. Check if required packages are installed
print_status "Checking Python dependencies..."
python -c "import fastapi, uvicorn, sqlalchemy, redis" || {
    print_error "Missing required packages. Installing..."
    pip install -r requirements.txt
}

# 5. Check environment variables
print_status "Checking environment configuration..."
if [ ! -f ".env" ]; then
    print_warning "No .env file found. Creating from .env.example..."
    cp .env.example .env
fi

# Check for required API keys
if ! grep -q "OPENROUTER_API_KEY" .env; then
    print_warning "OPENROUTER_API_KEY not found in .env file"
    print_warning "Please add your OpenRouter API key to .env file"
fi

# 6. Check database
print_status "Checking database..."
if [ ! -f "nextagi.db" ]; then
    print_warning "Database not found. Initializing..."
    python scripts/setup_database.py
fi

# 7. Check Redis connectivity
print_status "Checking Redis connectivity..."
redis-cli ping > /dev/null 2>&1 || {
    print_warning "Redis is not running. Starting Redis..."
    if command -v brew > /dev/null; then
        brew services start redis
    elif command -v systemctl > /dev/null; then
        sudo systemctl start redis
    else
        print_error "Cannot start Redis automatically. Please start Redis manually."
        exit 1
    fi
    sleep 2
}

# 8. Validate configuration on startup
print_status "Validating backend configuration..."
python -c "
import os
import sys
sys.path.append('.')
from backend.judge.config import settings
print(f'✅ Environment: {settings.environment}')
print(f'✅ Database URL: {settings.DATABASE_URL}')
print(f'✅ Redis URL: {settings.REDIS_URL}')
print(f'✅ Caching enabled: {settings.ENABLE_CACHING}')
print(f'✅ Worker in-process: {settings.RUN_WORKER_IN_PROCESS}')
"

# 9. Start the backend
print_status "Starting NextAGI backend..."
print_status "Backend will be available at: http://localhost:8000"
print_status "API documentation: http://localhost:8000/docs"
print_status "Health check: http://localhost:8000/health"
print_status "Press Ctrl+C to stop the server"
echo ""

# Start with proper error handling and logging
python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    --access-log \
    --use-colors
