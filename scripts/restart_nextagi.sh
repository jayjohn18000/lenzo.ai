#!/bin/bash
# Automated NextAGI restart script with proper configuration

set -e  # Exit on any error

echo "🚀 Starting NextAGI automated restart..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/jaylenjohnson18/lenzo.ai/lenzo.ai"
BACKEND_PORT=8000
FRONTEND_PORT=3000
TEST_API_KEY="nextagi_test-key-123"

# Environment variables
export NEXTAGI_DEV_MODE=true
export NEXTAGI_TEST_API_KEY="$TEST_API_KEY"
export DATABASE_URL="sqlite:///./nextagi.db"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Project Root: $PROJECT_ROOT"
echo "   Backend Port: $BACKEND_PORT"
echo "   Frontend Port: $FRONTEND_PORT"
echo "   Test API Key: $TEST_API_KEY"
echo "   Dev Mode: $NEXTAGI_DEV_MODE"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $port is in use${NC}"
        return 0
    else
        echo -e "${GREEN}✅ Port $port is available${NC}"
        return 1
    fi
}

# Function to kill processes on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}🔄 Killing processes on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}   Attempt $attempt/$max_attempts - waiting...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service_name failed to start within timeout${NC}"
    return 1
}

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${BLUE}📁 Changed to project directory: $(pwd)${NC}"

# Kill existing processes
echo -e "${YELLOW}🔄 Stopping existing services...${NC}"
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Seed database
echo -e "${BLUE}🌱 Seeding database with test users...${NC}"
python scripts/simple_seed.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database seeding completed${NC}"
else
    echo -e "${RED}❌ Database seeding failed${NC}"
    exit 1
fi

# Start backend
echo -e "${BLUE}🚀 Starting backend server...${NC}"
cd "$PROJECT_ROOT/backend"
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
if wait_for_service "http://localhost:$BACKEND_PORT/api/v1/health" "Backend"; then
    echo -e "${GREEN}✅ Backend started successfully${NC}"
else
    echo -e "${RED}❌ Backend failed to start${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Test authentication
echo -e "${BLUE}🔐 Testing authentication...${NC}"
AUTH_TEST=$(curl -s -H "Authorization: Bearer $TEST_API_KEY" "http://localhost:$BACKEND_PORT/api/v1/auth/test")
if echo "$AUTH_TEST" | grep -q "authenticated"; then
    echo -e "${GREEN}✅ Authentication test passed${NC}"
else
    echo -e "${RED}❌ Authentication test failed${NC}"
    echo "Response: $AUTH_TEST"
fi

# Start frontend
echo -e "${BLUE}🎨 Starting frontend server...${NC}"
cd "$PROJECT_ROOT/frontend"

# Ensure API key is set
echo "NEXT_PUBLIC_API_KEY=$TEST_API_KEY" > .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:$BACKEND_PORT" >> .env.local

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    npm install
fi

nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to be ready
if wait_for_service "http://localhost:$FRONTEND_PORT" "Frontend"; then
    echo -e "${GREEN}✅ Frontend started successfully${NC}"
else
    echo -e "${RED}❌ Frontend failed to start${NC}"
    kill $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

# Final health check
echo -e "${BLUE}🏥 Running final health checks...${NC}"

# Backend health
BACKEND_HEALTH=$(curl -s "http://localhost:$BACKEND_PORT/api/v1/health")
echo "Backend Health: $BACKEND_HEALTH"

# Auth health
AUTH_HEALTH=$(curl -s "http://localhost:$BACKEND_PORT/api/v1/auth/health")
echo "Auth Health: $AUTH_HEALTH"

# Frontend health
FRONTEND_HEALTH=$(curl -s "http://localhost:$FRONTEND_PORT" | head -c 100)
echo "Frontend Health: $FRONTEND_HEALTH"

echo -e "${GREEN}🎉 NextAGI restart completed successfully!${NC}"
echo -e "${BLUE}📋 Service URLs:${NC}"
echo "   Backend: http://localhost:$BACKEND_PORT"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   API Health: http://localhost:$BACKEND_PORT/api/v1/health"
echo "   Auth Health: http://localhost:$BACKEND_PORT/api/v1/auth/health"
echo "   Auth Test: http://localhost:$BACKEND_PORT/api/v1/auth/test"

echo -e "${BLUE}📋 Test Credentials:${NC}"
echo "   API Key: $TEST_API_KEY"
echo "   Test Command: curl -H \"Authorization: Bearer $TEST_API_KEY\" http://localhost:$BACKEND_PORT/api/v1/auth/test"

echo -e "${BLUE}📋 Process IDs:${NC}"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"

echo -e "${BLUE}📋 Logs:${NC}"
echo "   Backend: logs/backend.log"
echo "   Frontend: logs/frontend.log"

# Save PIDs for later cleanup
echo "$BACKEND_PID" > .nextagi_backend.pid
echo "$FRONTEND_PID" > .nextagi_frontend.pid

echo -e "${GREEN}✅ NextAGI is ready for use!${NC}"
