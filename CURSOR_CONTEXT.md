# NextAGI Project Context - Current State

## Project Overview
NextAGI is an advanced AI reliability platform that detects and prevents hallucinations in LLM outputs using proprietary HDM-2 (Hallucination Detection Model v2) and UQLM (Universal Query Language Model) technology. The platform targets high-stakes industries requiring 99.9%+ accuracy.

## Current Architecture Status
- **Frontend**: Next.js 15.5.0 running on port 3002 (http://localhost:3002)
- **Backend**: FastAPI with uvicorn running on port 8000 (http://localhost:8000)
- **Database**: SQLite (nextagi.db)
- **Cache**: Redis (localhost:6379)
- **Worker**: In-process QueryWorker for async job processing

## Recent Issues Resolved
1. **Frontend Fetch Error**: Fixed "Failed to fetch" TypeError by switching from full URLs to relative paths for API calls
2. **Backend Job Loop**: Resolved infinite 202 Accepted responses by ensuring worker processes jobs correctly
3. **Job Result Retrieval**: Fixed null results in API responses by implementing direct Redis retrieval
4. **UI Styling**: Enhanced visual design with gradients, shadows, and professional styling

## Current System State
- ✅ Frontend-backend pipeline fully functional
- ✅ Usage statistics API working (returns 9,644+ requests)
- ✅ Async job processing operational
- ✅ Query submission and result retrieval working
- ✅ Professional UI with enhanced styling

## Key Files Modified Recently
- `frontend/app/page.tsx`: Enhanced UI styling, fixed data fetching
- `frontend/lib/api.ts`: Updated to use relative API paths
- `backend/api/v1/routes.py`: Fixed job result retrieval logic
- `backend/main.py`: Worker initialization and Redis configuration

## Environment Setup
- Python virtual environment: `venv/` (activated)
- Environment variables: `RUN_WORKER_IN_PROCESS=true`, `PYTHONPATH=.`
- API Key: `nextagi_test-key-123` (development bypass enabled)

## Current Processes Running
- Frontend: Next.js dev server on port 3002
- Backend: FastAPI with uvicorn on port 8000
- Worker: In-process QueryWorker processing jobs from Redis queue

## API Endpoints Working
- `GET /api/v1/usage?days=7`: Returns usage statistics
- `POST /api/v1/query`: Submits queries for processing
- `GET /api/v1/jobs/{job_id}`: Retrieves job status and results

## Next Steps Available
1. Test complete end-to-end functionality
2. Add more sophisticated error handling
3. Implement additional features
4. Performance optimization
5. Security enhancements

## Technical Debt
- CSS inline styles warnings (non-critical)
- FastAPI deprecation warning for `on_event` (should migrate to lifespan handlers)

## Development Notes
- All critical functionality is working
- System is ready for feature development
- Both frontend and backend are responsive to changes
- Redis and database connections are stable
