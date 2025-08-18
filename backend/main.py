# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.judge.schemas import RouteRequest, RouteResponse, HealthResponse
from backend.judge.config import settings
from backend.judge.policy.dispatcher import decide_pipeline
from backend.judge.pipelines.runner import run_pipeline
from backend.judge.utils.trace import new_trace_id
import logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TruthRouter", version="0.1.0")

# CORS for local dev / Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Lightweight readiness check."""
    ok = bool(settings.OPENROUTER_API_KEY)
    return HealthResponse(status="ok" if ok else "degraded")


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    """
    Unified entrypoint:
      - decide pipeline (judge | tool_chain)
      - run selected pipeline
      - return normalized response with trace_id
    """
    trace_id = new_trace_id()
    try:
        pipeline_id, decision_reason = decide_pipeline(req)
        result = await run_pipeline(pipeline_id, req, trace_id=trace_id)

        # Citations are on for both pipelines; ensure key exists
        result.setdefault("citations", [])

        return RouteResponse(
            trace_id=trace_id,
            pipeline_id=pipeline_id,
            decision_reason=decision_reason,
            **result,
        )
    except HTTPException:
        # re-raise FastAPI HTTPExceptions as-is
        raise
    except Exception as e:
        # one consistent error envelope
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "trace_id": trace_id},
        )


# optional: `uvicorn backend.main:app --reload`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
