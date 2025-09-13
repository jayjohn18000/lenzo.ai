# 🚀 NextAGI Development Setup Guide

This guide will help you set up the NextAGI development environment quickly and efficiently.

## 📋 Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Redis** - [Install Redis](https://redis.io/download)
- **Git** - [Download Git](https://git-scm.com/downloads)

### Quick Redis Installation

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

## 🛠️ Quick Setup

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd nextagi

# Run the automated setup script
./scripts/setup_dev_environment.sh
```

The setup script will:
- ✅ Create virtual environment
- ✅ Install Python dependencies
- ✅ Setup environment variables
- ✅ Start Redis
- ✅ Initialize database
- ✅ Seed test users and API keys
- ✅ Install frontend dependencies

### 2. Start the Application

```bash
# Start backend (in one terminal)
./scripts/restart_backend.sh

# Start frontend (in another terminal)
cd frontend
npm run dev
```

### 3. Access the Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## 🔑 Test API Keys

The setup script creates multiple test users with different subscription tiers:

| Tier | API Key | Rate Limit | Use Case |
|------|---------|------------|----------|
| **Development** | `nextagi_test-key-123` | 1000/min, 100k/day | Development & testing |
| **Free** | `nextagi_free-key-456` | 5/min, 100/day | Free tier testing |
| **Starter** | `nextagi_starter-key-789` | 60/min, 1k/day | Starter tier testing |
| **Professional** | `nextagi_pro-key-101` | 300/min, 10k/day | Pro tier testing |

### Test API Usage

```bash
# Test with development key
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer nextagi_test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the capital of France?", "mode": "balanced"}'

# Test with free tier key
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer nextagi_free-key-456" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!", "mode": "speed"}'
```

## 🏗️ Manual Setup (Alternative)

If you prefer manual setup or the automated script fails:

### 1. Python Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env file with your API keys

# Initialize database
python scripts/setup_database.py

# Seed test users
python scripts/seed_test_users.py

# Start backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📁 Project Structure

```
nextagi/
├── backend/                 # FastAPI backend
│   ├── api/                # API routes
│   ├── auth/               # Authentication system
│   ├── judge/              # AI model routing & judging
│   ├── jobs/               # Async job processing
│   ├── middleware/         # Custom middleware
│   └── main.py             # Application entry point
├── frontend/               # Next.js frontend
│   ├── app/                # App router pages
│   ├── components/         # React components
│   ├── lib/                # Utilities and API client
│   └── package.json        # Frontend dependencies
├── scripts/                # Development scripts
│   ├── restart_backend.sh  # Backend restart automation
│   ├── seed_test_users.py  # Database seeding
│   └── setup_dev_environment.sh # Complete setup
└── requirements.txt        # Python dependencies
```

## 🔧 Development Scripts

### Backend Management

```bash
# Start/restart backend with proper configuration
./scripts/restart_backend.sh

# Reseed test users (if needed)
python scripts/seed_test_users.py

# Complete environment setup
./scripts/setup_dev_environment.sh
```

### Database Management

```bash
# Initialize database
python scripts/setup_database.py

# Seed test data
python scripts/seed_test_users.py

# Check database status
sqlite3 nextagi.db ".tables"
```

## 🧪 Testing

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Authentication health
curl http://localhost:8000/api/v1/auth/health

# Test query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer nextagi_test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test query", "mode": "balanced"}'
```

### Frontend Testing

```bash
# Start frontend
cd frontend && npm run dev

# Access at http://localhost:3000
# Test the query interface with different modes
```

## 🐛 Troubleshooting

### Common Issues

**1. Backend won't start:**
```bash
# Check if virtual environment is activated
source venv/bin/activate

# Check Python dependencies
pip install -r requirements.txt

# Check Redis is running
redis-cli ping
```

**2. Frontend won't start:**
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**3. API key authentication fails:**
```bash
# Check if test users are seeded
python scripts/seed_test_users.py

# Verify API key format
echo "nextagi_test-key-123" | sha256sum
```

**4. Redis connection issues:**
```bash
# Start Redis
brew services start redis  # macOS
sudo systemctl start redis  # Linux

# Test connection
redis-cli ping
```

### Logs and Debugging

**Backend logs:**
```bash
# Start with debug logging
python -m uvicorn backend.main:app --log-level debug
```

**Frontend logs:**
```bash
# Check browser console for frontend errors
# Check terminal for build errors
```

## 🚀 Production Deployment

For production deployment, see the main README.md for Docker and deployment instructions.

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

If you encounter issues:
1. Check this troubleshooting guide
2. Review the logs
3. Check the API documentation
4. Create an issue with detailed information

---

**Happy coding! 🚀**

The NextAGI team has made development as smooth as possible with automated scripts and comprehensive test data. All PocketFlow tickets have been implemented and the system is fully operational!
