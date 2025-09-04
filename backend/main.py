# backend/main.py
"""
Enhanced main application that integrates all NextAGI components:
- Smart model selection
- Enhanced scoring engine
- API key authentication
- Usage tracking and billing
- Revenue optimization features
- Complete job queue management
- Real-time monitoring and analytics
- Development and debug endpoints
"""

from __future__ import annotations

import time
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import redis.asyncio as aioredis

# Import all the enhanced components
from backend.judge.schemas import RouteRequest, RouteResponse, HealthResponse
from backend.judge.config import settings
from backend.judge.policy.dispatcher import decide_pipeline
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.utils.trace import new_trace_id
from backend.auth.api_key import Base as AuthBase, verify_api_key
from backend.api.v1.routes import router as api_router
from backend.judge.model_selector import SmartModelSelector
from backend.judge.steps.enhanced_scoring import EnhancedScorer

# Job system imports
from backend.jobs.models import Base as JobBase
from backend.dependencies import init_dependencies
from backend.jobs.worker import QueryWorker  # Worker is instantiated from JobManager inside deps

# Additional integrations
from backend.judge.utils.cache import get_cache
from backend.middleware.validation import DataValidationMiddleware
from backend.api.v1.stats import stats_router

# Analytics DB (optional but supported)
from backend.database.models import Base as AnalyticsBase  # noqa: F401

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
model_selector = SmartModelSelector()
enhanced_scorer = EnhancedScorer()
redis_client = None
job_manager = None
worker_task: asyncio.Task | None = None
cache_instance = None
session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with comprehensive initialization"""
    global redis_client, job_manager, worker_task, cache_instance, session_factory

    logger.info("🚀 Starting NextAGI...")

    # 1) Database init
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

        # Create tables for all used Bases (idempotent)
        AuthBase.metadata.create_all(bind=engine)
        JobBase.metadata.create_all(bind=engine)
        try:
            AnalyticsBase.metadata.create_all(bind=engine)  # optional analytics tables, if present
            logger.info("✅ Analytics tables ensured")
        except Exception as e:
            logger.warning(f"⚠️ Skipping analytics tables creation: {e}")

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

    # 2) Redis init (prefers REDIS_URL; falls back to host/port)
    try:
        # Decode responses so we always get str from Redis (matches worker/manager expectations)
        redis_client = aioredis.from_url(
            settings.redis_dsn(0),
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
        )
        await redis_client.ping()

        # Log effective Redis connection details for parity debug
        try:
            pool = redis_client.connection_pool
            kw = getattr(pool, "connection_kwargs", {})
            logger.info(
                "✅ Redis connected (host=%s port=%s db=%s decode_responses=%s)",
                kw.get("host"),
                kw.get("port"),
                kw.get("db"),
                getattr(redis_client, "decode_responses", None),
            )
        except Exception:
            logger.info("✅ Redis connection established (details unavailable)")

        # 3) Job system wiring
        try:
            # Construct JobManager(redis_client, session_factory) *inside* init_dependencies
            job_manager = init_dependencies(redis_client, session_factory)
            logger.info("✅ Job dependencies initialized")

            # Optionally run worker in-process
            if settings.RUN_WORKER_IN_PROCESS:
                worker = QueryWorker(job_manager)
                worker_task = asyncio.create_task(worker.start())
                logger.info("✅ Background worker started in-process")
                asyncio.create_task(monitor_worker_health(worker_task))
            else:
                logger.info("ℹ️ RUN_WORKER_IN_PROCESS is False — not starting in-process worker")

        except Exception as e:
            logger.error(f"❌ Job system initialization failed: {e}")
            logger.warning("⚠️ Running without async job support")

    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        logger.warning("⚠️ Running without Redis-dependent features")
        redis_client = None
        job_manager = None
        worker_task = None

    # 4) Cache init (non-fatal)
    try:
        cache_instance = await get_cache()
        logger.info("✅ Cache initialized")
        asyncio.create_task(warmup_cache())
    except Exception as e:
        logger.warning(f"⚠️ Cache initialization failed: {e}")
        cache_instance = None

    # 5) Model selector history
    try:
        await model_selector.load_performance_history()
        logger.info("✅ Model performance history loaded")
    except Exception as e:
        logger.warning(f"⚠️ Model performance history unavailable: {e}")

    # 6) API keys quick audit
    api_key_checks = [
        ("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY),
        ("ANTHROPIC_API_KEY", getattr(settings, "ANTHROPIC_API_KEY", None)),
        ("OPENAI_API_KEY", getattr(settings, "OPENAI_API_KEY", None)),
    ]
    configured_keys = sum(1 for _, v in api_key_checks if v)
    for key_name, key_value in api_key_checks:
        logger.info(f"{'✅' if key_value else '⚠️'} {key_name} {'configured' if key_value else 'not configured'}")
    logger.info(f"✅ API Keys: {configured_keys}/{len(api_key_checks)} configured")

    # 7) Startup health check (non-fatal)
    health_status = await perform_startup_health_check()
    if health_status["status"] != "healthy":
        logger.warning(f"⚠️ System started with status: {health_status['status']}")

    logger.info("🎉 NextAGI startup completed successfully!")
    asyncio.create_task(system_monitor())

    yield  # ----- App runs -----

    # ===== Shutdown =====
    logger.info("🛑 Shutting down NextAGI...")

    # Stop worker
    if worker_task:
        logger.info("Stopping background worker...")
        worker_task.cancel()
        try:
            await asyncio.wait_for(worker_task, timeout=10.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            logger.info("Worker stopped")

    # Save model performance history
    try:
        await model_selector.save_performance_history()
        logger.info("✅ Model performance history saved")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save performance history: {e}")

    # Close cache
    if cache_instance:
        try:
            await cache_instance.close()
            logger.info("✅ Cache connections closed")
        except Exception as e:
            logger.warning(f"⚠️ Cache cleanup failed: {e}")

    # Close Redis
    if redis_client:
        try:
            # redis-py asyncio supports .close() (sync) + .wait_closed() or aclose() in newer versions
            close = getattr(redis_client, "aclose", None)
            if callable(close):
                await redis_client.aclose()
            else:
                redis_client.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.warning(f"⚠️ Redis cleanup failed: {e}")

    logger.info("👋 NextAGI shutdown completed")


# Background monitoring / utilities
async def monitor_worker_health(task: asyncio.Task):
    while True:
        try:
            if task.done():
                exc = task.exception()
                if exc:
                    logger.error(f"Worker crashed: {exc!r}")
                break
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Worker monitoring error: {e}")
            break


async def warmup_cache():
    if not cache_instance:
        return
    try:
        # Add warmup routines if desired
        logger.info("🔥 Cache warmup completed")
    except Exception as e:
        logger.warning(f"Cache warmup failed: {e}")


async def system_monitor():
    while True:
        try:
            await asyncio.sleep(300)
            if redis_client:
                await redis_client.ping()
            logger.debug("System health check passed")
        except Exception as e:
            logger.warning(f"System monitor detected issue: {e}")


async def perform_startup_health_check():
    checks = {}

    # DB
    try:
        engine = create_engine(settings.DATABASE_URL, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Redis
    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = "healthy"
        except Exception as e:
            checks["redis"] = f"unhealthy: {e}"
    else:
        checks["redis"] = "not_configured"

    # API keys (require OpenRouter at minimum)
    api_key_ok = bool(settings.OPENROUTER_API_KEY)
    checks["api_keys"] = "healthy" if api_key_ok else "missing_required_keys"

    # Overall
    if any("unhealthy" in str(v) for v in checks.values()):
        status = "unhealthy"
    elif any("not_configured" in str(v) for v in checks.values()):
        status = "degraded"
    else:
        status = "healthy"

    return {"status": status, "checks": checks, "timestamp": time.time()}


# Create FastAPI app
app = FastAPI(
    title="NextAGI - Advanced Multi-LLM Truth Router",
    version="2.0.0",
    description="""
    NextAGI routes your queries to multiple leading AI models, evaluates their responses 
    using advanced scoring algorithms, and returns the most accurate, trustworthy answer.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Core", "description": "Main routing and query processing"},
        {"name": "Statistics", "description": "Usage analytics and metrics"},
        {"name": "Admin", "description": "Administrative endpoints"},
        {"name": "Development", "description": "Development and debugging tools"},
        {"name": "Health", "description": "System health and monitoring"},
    ],
)

# Middleware
app.add_middleware(DataValidationMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["nextagi.com", "*.nextagi.com", "localhost", "127.0.0.1"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://nextagi.com",
        "https://*.nextagi.com",
    ]
    if not settings.DEBUG
    else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)


# Request logging
@app.middleware("http")
async def enhanced_request_logging(request, call_next):
    start_time = time.time()
    request_id = new_trace_id()
    request.state.request_id = request_id

    logger.info(
        f"📥 {request.method} {request.url.path} "
        f"[{request_id[:8]}] from {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"📤 {request.method} {request.url.path} "
            f"[{request_id[:8]}] - {response.status_code} - {process_time:.3f}s"
        )
        if process_time > 5.0:
            logger.warning(f"🐌 Slow request: {process_time:.3f}s for {request.url.path}")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"💥 {request.method} {request.url.path} "
            f"[{request_id[:8]}] - ERROR after {process_time:.3f}s: {str(e)}"
        )
        raise


# Routers
app.include_router(api_router, tags=["Core"])
app.include_router(stats_router, tags=["Statistics"])


# ===== Health =====
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def enhanced_health_check():
    health_data = await perform_startup_health_check()
    health_data["uptime_seconds"] = time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0
    health_data["worker_status"] = "running" if worker_task and not worker_task.done() else "stopped"
    available_models = len(settings.DEFAULT_MODELS) if settings.OPENROUTER_API_KEY else 0
    health_data["available_models"] = available_models

    return HealthResponse(
        status=health_data["status"],
        available_models=available_models,
        last_test_time=None,
    )


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    health_data = await perform_startup_health_check()
    metrics = {}
    if redis_client:
        try:
            info = await redis_client.info()
            metrics["redis_memory"] = info.get("used_memory_human", "unknown")
            metrics["redis_connections"] = info.get("connected_clients", 0)
        except Exception:
            pass

    health_data["metrics"] = metrics
    health_data["components"] = {
        "job_manager": "active" if job_manager else "inactive",
        "worker": "running" if worker_task and not worker_task.done() else "stopped",
        "cache": "active" if cache_instance else "inactive",
        "model_selector": "loaded" if model_selector else "inactive",
    }
    return health_data


# ===== Core routing =====
@app.post("/route", response_model=RouteResponse, tags=["Core"])
async def enhanced_route(req: RouteRequest, background_tasks: BackgroundTasks, api_key_info: dict = Depends(verify_api_key)):
    trace_id = new_trace_id()
    start_time = time.perf_counter()

    logger.info(f"[{trace_id}] Enhanced route request from user {api_key_info['user_id']}")
    logger.info(f"[{trace_id}] Prompt: {req.prompt[:100]}...")

    try:
        # Smart selection
        if not req.options.models:
            try:
                selected = model_selector.select_models(
                    req.prompt,
                    getattr(model_selector.SelectionMode, req.options.model_selection_mode.upper()),
                    max_models=4,
                )
                req.options.models = selected
                logger.info(f"[{trace_id}] Smart model selection: {selected}")
            except Exception as e:
                logger.warning(f"[{trace_id}] Model selection failed, using defaults: {e}")
                req.options.models = settings.DEFAULT_MODELS[:3]

        pipeline_id, decision_reason = decide_pipeline(req)
        logger.info(f"[{trace_id}] Pipeline selected: {pipeline_id} ({decision_reason})")

        # Cache → run pipeline
        try:
            if cache_instance:
                cached = await cache_instance.get(
                    req.prompt, req.options.models, req.expected_traits, req.options.model_selection_mode
                )
                if cached:
                    logger.info(f"[{trace_id}] Returning cached result")
                    cached["trace_id"] = trace_id
                    cached["from_cache"] = True
                    return RouteResponse(**cached)

            result = await run_pipeline(pipeline_id, req, trace_id=trace_id)

            # Enhanced scorer if needed
            if pipeline_id == "judge" and result.get("confidence", 0) < 0.9:
                logger.info(f"[{trace_id}] Applying enhanced scoring for low confidence result")
                try:
                    improved = enhanced_scorer.enhance_confidence(result)
                    result.update(improved)
                except Exception as e:
                    logger.warning(f"[{trace_id}] Enhanced scoring failed: {e}")

            if cache_instance and result.get("confidence", 0) > 0.7:
                background_tasks.add_task(
                    cache_instance.set,
                    req.prompt,
                    req.options.models,
                    result,
                    req.expected_traits,
                    req.options.model_selection_mode,
                )

        except Exception as pipeline_error:
            logger.error(f"[{trace_id}] Pipeline execution failed: {pipeline_error}")
            raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(pipeline_error)}")

        result.setdefault("citations", [])
        result.setdefault("models_attempted", req.options.models or [])
        result.setdefault("models_succeeded", result.get("models_attempted", []))

        response_time_ms = int((time.perf_counter() - start_time) * 1000)
        result["response_time_ms"] = response_time_ms

        if result.get("winner_model") and result.get("confidence"):
            background_tasks.add_task(
                model_selector.update_performance_history,
                result["winner_model"],
                True,
                response_time_ms,
                result["confidence"],
            )

        background_tasks.add_task(track_usage_analytics, api_key_info, req, result, response_time_ms)

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
            trace_id=trace_id,
        )

        logger.info(f"[{trace_id}] Request completed successfully in {response_time_ms}ms")
        return enhanced_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Request failed: {str(e)}")
        if req.options.models:
            for model in req.options.models:
                background_tasks.add_task(
                    model_selector.update_performance_history,
                    model,
                    False,
                    int((time.perf_counter() - start_time) * 1000),
                    0.0,
                )
        raise HTTPException(status_code=500, detail=f"Request processing failed: {str(e)}")


# ===== Admin =====
@app.get("/admin/stats", tags=["Admin"])
async def admin_stats(api_key_info: dict = Depends(verify_api_key)):
    if api_key_info["subscription_tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise access required")

    try:
        health_data = await perform_startup_health_check()
        stats = {
            "system_health": health_data,
            "model_performance": model_selector.performance_history,
            "cache_metrics": await cache_instance.get_metrics() if cache_instance else {},
            "job_queue_stats": await get_job_queue_stats() if job_manager else {},
            "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0,
            "active_connections": "Would query from connection pool",
            "total_requests_today": "Would query from database",
            "average_response_time": "Would calculate from recent requests",
            "error_rate_last_hour": "Would calculate from logs",
        }
        return stats
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/admin/jobs", tags=["Admin"])
async def admin_jobs(api_key_info: dict = Depends(verify_api_key)):
    if api_key_info["subscription_tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise access required")
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job system not available")
    try:
        return await get_job_queue_stats()
    except Exception as e:
        logger.error(f"Job queue stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job statistics")


# ===== Development =====
@app.post("/dev/route", response_model=RouteResponse, tags=["Development"])
async def dev_route(req: RouteRequest, background_tasks: BackgroundTasks):
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    logger.info("🧪 Using development route (no auth)")

    mock_api_key_info = {"user_id": 1, "user_email": "dev@localhost", "subscription_tier": "professional", "api_key_id": 1}
    return await enhanced_route(req, background_tasks, mock_api_key_info)


@app.get("/dev/health", tags=["Development"])
async def dev_health():
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "status": "ok",
        "mode": "development",
        "message": "NextAGI development server running",
        "timestamp": time.time(),
        "components": {
            "redis": "connected" if redis_client else "disconnected",
            "job_manager": "active" if job_manager else "inactive",
            "worker": "running" if worker_task and not worker_task.done() else "stopped",
        },
    }


@app.post("/dev/query", tags=["Development"])
async def dev_query(req: dict):
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    logger.info("🧪 Using development query endpoint (no auth)")
    try:
        prompt = req.get("prompt", "test")
        return {
            "request_id": f"dev-{int(time.time())}",
            "answer": f"Development mode response for: '{prompt}'. Your text input is working! Backend connection successful.",
            "confidence": 0.95,
            "winner_model": "development-mock",
            "response_time_ms": 150,
            "models_used": ["mock-model-1", "mock-model-2"],
            "reasoning": "This is a development mock response to test connectivity.",
            "system_status": {
                "redis": "connected" if redis_client else "disconnected",
                "worker": "running" if worker_task and not worker_task.done() else "stopped",
                "cache": "active" if cache_instance else "inactive",
            },
        }
    except Exception as e:
        logger.error(f"Dev endpoint error: {e}")
        return {
            "request_id": "dev-error",
            "answer": f"Development endpoint error: {str(e)}",
            "confidence": 0.0,
            "winner_model": "error",
            "response_time_ms": 0,
            "models_used": [],
            "reasoning": None,
            "error": str(e),
        }


# ===== Debug/test =====
@app.get("/debug/routes", tags=["Development"])
async def debug_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            info = {"path": route.path, "methods": list(route.methods) if route.methods else [], "name": getattr(route, "name", "unnamed"), "tags": getattr(route, "tags", [])}
            if hasattr(route, "endpoint") and hasattr(route.endpoint, "__doc__"):
                info["description"] = route.endpoint.__doc__.strip() if route.endpoint.__doc__ else None
            routes.append(info)

    return {
        "total_routes": len(routes),
        "available_routes": sorted(routes, key=lambda x: x["path"]),
        "system_info": {
            "debug_mode": settings.DEBUG,
            "version": "2.0.0",
            "components": {
                "redis": "connected" if redis_client else "disconnected",
                "worker": "running" if worker_task and not worker_task.done() else "stopped",
                "cache": "active" if cache_instance else "inactive",
            },
        },
    }


@app.get("/test/ping", tags=["Development"])
async def test_ping():
    return {"message": "pong", "timestamp": time.time(), "server": "NextAGI v2.0.0", "status": "operational"}


@app.post("/api/simple-query", tags=["Development"])
async def simple_query_without_auth(request: dict):
    try:
        prompt = request.get("prompt", "test")
        return {
            "request_id": f"test_{int(time.time())}",
            "answer": f"Backend is running! Received: {prompt}",
            "confidence": 0.9,
            "winner_model": "test-model",
            "models_used": ["test-model"],
            "response_time_ms": 100,
            "reasoning": "Simple test response - backend is working",
            "system_health": "operational",
        }
    except Exception as e:
        return {"error": str(e), "request_id": f"error_{int(time.time())}", "system_health": "error"}


@app.get("/debug/system", tags=["Development"])
async def debug_system():
    debug_info = {
        "system_status": await perform_startup_health_check(),
        "configuration": {
            "debug_mode": settings.DEBUG,
            "database_url": settings.DATABASE_URL,
            "redis_configured": bool(redis_client),
            "api_keys_configured": bool(settings.OPENROUTER_API_KEY),
        },
        "runtime_info": {
            "worker_running": bool(worker_task and not worker_task.done()),
            "cache_active": bool(cache_instance),
            "job_manager_active": bool(job_manager),
        },
        "performance": {
            "model_count": len(model_selector.performance_history),
            "cache_metrics": await cache_instance.get_metrics() if cache_instance else {},
        },
    }
    return debug_info


# ===== Root =====
@app.get("/", tags=["Core"])
async def root():
    return {
        "message": "Welcome to NextAGI - Advanced Multi-LLM Truth Router",
        "version": "2.0.0",
        "status": "operational",
        "documentation": {"docs_url": "/docs", "redoc_url": "/redoc", "health_check": "/health"},
        "api_endpoints": {"core": "/route", "enhanced_query": "/api/v1/query", "statistics": "/api/v1/usage", "admin": "/admin/stats"},
        "development_endpoints": {"available_in_debug": settings.DEBUG, "dev_query": "/dev/query", "test_ping": "/test/ping", "debug_routes": "/debug/routes"},
        "system_info": {
            "components_active": {
                "redis": bool(redis_client),
                "worker": bool(worker_task and not worker_task.done()),
                "cache": bool(cache_instance),
                "job_manager": bool(job_manager),
            },
            "features": [
                "Smart model selection",
                "Advanced confidence scoring",
                "Async job processing",
                "Real-time caching",
                "Usage analytics",
                "Performance optimization",
            ],
        },
        "timestamp": time.time(),
    }


# ===== Error handlers =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    error_detail = {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": time.time(),
        "path": request.url.path,
        "method": request.method,
    }
    if hasattr(request.state, "request_id"):
        error_detail["request_id"] = request.state.request_id
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} on {request.method} {request.url.path}")
    return JSONResponse(status_code=exc.status_code, content=error_detail)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    error_detail = {
        "error": "Internal server error",
        "status_code": 500,
        "timestamp": time.time(),
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
    }
    if settings.DEBUG:
        error_detail["debug_info"] = {"exception_type": type(exc).__name__, "exception_message": str(exc)}
    logger.error(f"💥 Unhandled exception [{request_id}]: {type(exc).__name__}: {str(exc)} on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content=error_detail)


# ===== Background tasks =====
async def track_usage_analytics(api_key_info, request, result, response_time):
    try:
        logger.debug(f"Tracking usage for user {api_key_info['user_id']}: {response_time}ms")
    except Exception as e:
        logger.error(f"Usage tracking failed: {e}")


async def get_job_queue_stats():
    if not redis_client:
        return {"error": "Redis not available"}
    try:
        # Prefer configured queue names
        pending = await redis_client.llen(settings.REDIS_JOB_QUEUE)
        processing_key = f"{settings.REDIS_JOB_QUEUE}:processing"
        processing = await redis_client.llen(processing_key)
        return {
            "pending_jobs": pending,
            "processing_jobs": processing,
            "worker_active": bool(worker_task and not worker_task.done()),
            "total_processed": "Would query from database",
        }
    except Exception as e:
        return {"error": str(e)}


# ===== App startup stamp =====
@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    logger.info(f"NextAGI application started at {app.state.start_time}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True,
    )
