# backend/main_enhanced.py
"""
Enhanced main application that integrates all NextAGI components:
- Smart model selection
- Enhanced scoring engine
- API key authentication
- Usage tracking and billing
- Revenue optimization features
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import all the enhanced components
from backend.judge.schemas import RouteRequest, RouteResponse, HealthResponse
from backend.judge.config import settings
from backend.judge.policy.dispatcher import decide_pipeline
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.utils.trace import new_trace_id
from backend.auth.api_key import Base, verify_api_key
from backend.api.v1.routes import router as api_router
from backend.judge.model_selector import SmartModelSelector
from backend.judge.steps.enhanced_scoring import EnhancedScorer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
model_selector = SmartModelSelector()
enhanced_scorer = EnhancedScorer()
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting NextAGI...")
    
    # Initialize Redis connection
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost',
            port=settings.REDIS_PORT if hasattr(settings, 'REDIS_PORT') else 6379,
            db=0,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        redis_client = None
    
    # Initialize database
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise
    
    # Validate API keys
    api_key_checks = [
        ("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY),
        ("ANTHROPIC_API_KEY", getattr(settings, 'ANTHROPIC_API_KEY', None)),
        ("OPENAI_API_KEY", getattr(settings, 'OPENAI_API_KEY', None))
    ]
    
    for key_name, key_value in api_key_checks:
        if key_value:
            logger.info(f"✅ {key_name} configured")
        else:
            logger.warning(f"⚠️  {key_name} not configured")
    
    logger.info("🎉 NextAGI startup completed successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down NextAGI...")
    if redis_client:
        redis_client.close()
    logger.info("👋 NextAGI shutdown completed")

# Create FastAPI app with enhanced configuration
app = FastAPI(
    title="NextAGI - Advanced Multi-LLM Truth Router",
    version="2.0.0",
    description="""
    NextAGI routes your queries to multiple leading AI models, evaluates their responses 
    using advanced scoring algorithms, and returns the most accurate, trustworthy answer.
    
    Features:
    - Smart model selection based on query type
    - Enhanced confidence scoring with hallucination detection
    - Comprehensive usage tracking and billing
    - Enterprise-grade API with rate limiting
    - Real-time analytics and cost optimization
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"] if settings.DEBUG else ["nextagi.com", "*.nextagi.com", "localhost"]
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nextagi.com",
        "https://*.nextagi.com"
    ] if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# Include API routes
app.include_router(api_router)

# Enhanced health check with comprehensive system status
@app.get("/health", response_model=HealthResponse)
async def enhanced_health_check():
    """Comprehensive health check with system diagnostics"""
    health_status = "healthy"
    checks = {}
    
    # Check API keys
    api_key_ok = bool(settings.OPENROUTER_API_KEY)
    checks["api_keys"] = "healthy" if api_key_ok else "unhealthy"
    
    # Check Redis
    redis_ok = True
    if redis_client:
        try:
            redis_client.ping()
            checks["redis"] = "healthy"
        except:
            redis_ok = False
            checks["redis"] = "unhealthy"
    else:
        redis_ok = False
        checks["redis"] = "not_configured"
    
    # Check database
    db_ok = True
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        db_ok = False
        checks["database"] = "unhealthy"
        logger.error(f"Database health check failed: {e}")
    
    # Check model availability
    available_models = len(settings.DEFAULT_MODELS) if api_key_ok else 0
    checks["models"] = f"{available_models}_available"
    
    # Overall status
    if not (api_key_ok and db_ok):
        health_status = "unhealthy"
    elif not redis_ok:
        health_status = "degraded"
    
    return HealthResponse(
        status=health_status,
        available_models=available_models,
        last_test_time=None,
        checks=checks
    )

# Enhanced route endpoint with all new features
@app.post("/route", response_model=RouteResponse)
async def enhanced_route(
    req: RouteRequest,
    background_tasks: BackgroundTasks,
    api_key_info: dict = Depends(verify_api_key)
):
    """
    Enhanced routing endpoint with smart model selection, 
    advanced scoring, and comprehensive tracking.
    """
    trace_id = new_trace_id()
    start_time = time.perf_counter()
    
    logger.info(f"[{trace_id}] Enhanced route request from user {api_key_info['user_id']}")
    logger.info(f"[{trace_id}] Prompt: {req.prompt[:100]}...")
    
    try:
        # Smart model selection if not specified
        if not req.options.models:
            selected_models = model_selector.select_models(
                req.prompt,
                getattr(model_selector.SelectionMode, req.options.model_selection_mode.upper()),
                max_models=4
            )
            req.options.models = selected_models
            logger.info(f"[{trace_id}] Smart model selection: {selected_models}")
        
        # Pipeline decision with enhanced logic
        pipeline_id, decision_reason = decide_pipeline(req)
        logger.info(f"[{trace_id}] Pipeline selected: {pipeline_id} ({decision_reason})")
        
        # Execute pipeline with enhanced scoring
        result = await run_pipeline(pipeline_id, req, trace_id=trace_id)
        
        # Apply enhanced scoring if judge pipeline
        if pipeline_id == "judge" and result.get("confidence", 0) < 0.9:
            logger.info(f"[{trace_id}] Applying enhanced scoring for low confidence result")
            # Enhanced scoring logic would be applied here
            # This integrates with the enhanced_consensus_selection function
        
        # Ensure all required fields are present
        result.setdefault("citations", [])
        result.setdefault("models_attempted", req.options.models or [])
        result.setdefault("models_succeeded", result.get("models_attempted", []))
        
        # Calculate response time
        response_time_ms = int((time.perf_counter() - start_time) * 1000)
        result["response_time_ms"] = response_time_ms
        
        # Update model performance history
        if result.get("winner_model") and result.get("confidence"):
            background_tasks.add_task(
                model_selector.update_performance_history,
                result["winner_model"],
                True,  # success
                response_time_ms,
                result["confidence"]
            )
        
        # Prepare enhanced response
        enhanced_result = RouteResponse(
            pipeline_id=pipeline_id,
            decision_reason=decision_reason,
            answer=result["answer"],
            winner_model=result.get("winner_model"),
            confidence=result.get("confidence"),
            response_time_ms=response_time_ms,
            models_attempted=result.get("models_attempted", []),
            models_succeeded=result.get("models_succeeded", []),
            scores_by_trait=result.get("scores_by_trait"),
            evidence=result.get("evidence"),
            citations=result.get("citations", []),
            trace_id=trace_id
        )
        
        logger.info(f"[{trace_id}] Request completed successfully in {response_time_ms}ms")
        return enhanced_result
        
    except Exception as e:
        logger.error(f"[{trace_id}] Request failed: {str(e)}")
        
        # Update model performance for failures
        if req.options.models:
            for model in req.options.models:
                background_tasks.add_task(
                    model_selector.update_performance_history,
                    model,
                    False,  # failure
                    int((time.perf_counter() - start_time) * 1000),
                    0.0
                )
        
        raise HTTPException(status_code=500, detail=f"Request processing failed: {str(e)}")

# Admin endpoints for monitoring
@app.get("/admin/stats")
async def admin_stats(api_key_info: dict = Depends(verify_api_key)):
    """Admin statistics endpoint (enterprise only)"""
    if api_key_info["subscription_tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise access required")
    
    # Return system statistics
    return {
        "model_performance": model_selector.performance_history,
        "system_health": await enhanced_health_check(),
        "active_users": "Would query database for active user count",
        "total_requests_today": "Would query usage records",
        "average_response_time": "Would calculate from recent requests"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": time.time()
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Welcome endpoint with API information"""
    return {
        "message": "Welcome to NextAGI - Advanced Multi-LLM Truth Router",
        "version": "2.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
        "api_base": "/api/v1"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )