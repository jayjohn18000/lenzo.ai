#!/bin/bash

# NextAGI Development Environment Setup Script
# Complete setup for development environment

set -e  # Exit on any error

echo "🚀 NextAGI Development Environment Setup"
echo "======================================="

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

print_status "Setting up NextAGI development environment..."

# 1. Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
print_success "Python version: $python_version"

# 2. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# 3. Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# 4. Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

# 5. Setup environment variables
print_status "Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env file from .env.example"
    else
        print_warning "No .env.example found. Please create .env file manually"
    fi
else
    print_success ".env file already exists"
fi

# 6. Check for required API keys
print_status "Checking API keys..."
if ! grep -q "OPENROUTER_API_KEY" .env; then
    print_warning "OPENROUTER_API_KEY not found in .env file"
    print_warning "Please add your OpenRouter API key to .env file"
    echo "Example: OPENROUTER_API_KEY=your_key_here"
fi

# 7. Setup Redis
print_status "Setting up Redis..."
if command -v redis-cli > /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is running"
    else
        print_status "Starting Redis..."
        if command -v brew > /dev/null; then
            brew services start redis
        elif command -v systemctl > /dev/null; then
            sudo systemctl start redis
        else
            print_warning "Cannot start Redis automatically. Please start Redis manually."
        fi
        sleep 2
        
        if redis-cli ping > /dev/null 2>&1; then
            print_success "Redis started successfully"
        else
            print_error "Failed to start Redis. Please start Redis manually."
            exit 1
        fi
    fi
else
    print_error "Redis is not installed. Please install Redis first."
    print_status "On macOS: brew install redis"
    print_status "On Ubuntu: sudo apt-get install redis-server"
    exit 1
fi

# 8. Setup database
print_status "Setting up database..."
if [ ! -f "nextagi.db" ]; then
    print_status "Initializing database..."
    python scripts/setup_database.py
    print_success "Database initialized"
else
    print_success "Database already exists"
fi

# 9. Seed test users
print_status "Seeding test users..."
python scripts/seed_test_users.py
print_success "Test users seeded"

# 10. Setup frontend dependencies
print_status "Setting up frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi
cd ..

# 11. Validate setup
print_status "Validating setup..."
source venv/bin/activate
python -c "
import sys
sys.path.append('.')
try:
    from backend.judge.config import settings
    print(f'✅ Configuration loaded successfully')
    print(f'✅ Environment: {settings.environment}')
    print(f'✅ Database: {settings.DATABASE_URL}')
    print(f'✅ Redis: {settings.REDIS_URL}')
    print(f'✅ Caching: {settings.ENABLE_CACHING}')
    print(f'✅ Worker: {settings.RUN_WORKER_IN_PROCESS}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

# 12. Final instructions
print_success "Development environment setup complete!"
echo ""
echo "🎉 NextAGI Development Environment Ready!"
echo "========================================"
echo ""
echo "📋 Available Scripts:"
echo "  ./scripts/restart_backend.sh  - Start/restart backend"
echo "  ./scripts/seed_test_users.py  - Reseed test users"
echo ""
echo "🚀 Quick Start:"
echo "  1. Start backend:   ./scripts/restart_backend.sh"
echo "  2. Start frontend:  cd frontend && npm run dev"
echo "  3. Open browser:    http://localhost:3000"
echo ""
echo "🔑 Test API Keys:"
echo "  Development: nextagi_test-key-123"
echo "  Free tier:   nextagi_free-key-456"
echo "  Starter:     nextagi_starter-key-789"
echo "  Professional: nextagi_pro-key-101"
echo ""
echo "📚 Documentation:"
echo "  Backend API:  http://localhost:8000/docs"
echo "  Health check: http://localhost:8000/health"
echo "  Auth health:  http://localhost:8000/api/v1/auth/health"
echo ""
print_success "Happy coding! 🚀"
