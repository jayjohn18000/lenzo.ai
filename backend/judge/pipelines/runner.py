import redis
from backend.judge.config import settings
import hashlib
# backend/judge/pipelines/runner.py
"""
Main pipeline runner that orchestrates different execution strategies
"""

import time
import logging
from typing import Dict, Any
from backend.judge.schemas import RouteRequest, PipelineID
from backend.judge.pipelines.judge import run_judge
from backend.judge.pipelines.tool_chain import run_tool_chain
from backend.judge.policy.dispatcher import should_escalate_after_prepass
from backend.judge.pipelines.judge import run_judge

logger = logging.getLogger(__name__)


async def run_pipeline(
    pipeline_id: PipelineID, req: RouteRequest, trace_id: str
) -> Dict[str, Any]:
    """
    Execute the specified pipeline and return structured results
    """
    start_time = time.perf_counter()

    try:
        logger.info(f"[{trace_id}] Starting {pipeline_id} pipeline")

        if pipeline_id == "judge":
            result = await run_judge(req, trace_id)

            # Check if we should escalate to tool_chain based on confidence
            confidence = result.get("confidence", 0.0)
            if should_escalate_after_prepass(confidence, req):
                # [PocketFlow] cache-wrap
                _pf_redis = None
                if getattr(settings, 'ENABLE_CACHING', False):
                    try:
                        _pf_redis = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
                        ck = _cache_key(locals().get('request') or locals().get('payload') or {})
                        if _pf_redis:
                            cached = _pf_redis.get(ck)
                            if cached:
                                return json.loads(cached)
                    except Exception:
                        pass

                logger.info(
                    f"[{trace_id}] Escalating to tool_chain (confidence: {confidence:.3f})"
                )
                result = await run_tool_chain(req, trace_id)
                result["escalated"] = True

        elif pipeline_id == "tool_chain":
            result = await run_tool_chain(req, trace_id)

        else:
            raise ValueError(f"Unknown pipeline_id: {pipeline_id}")

        # Add common metadata
        end_time = time.perf_counter()
        result.update(
            {
                "pipeline_id": pipeline_id,
                "response_time_ms": int((end_time - start_time) * 1000),
                "trace_id": trace_id,
            }
        )

        logger.info(
            f"[{trace_id}] Completed {pipeline_id} pipeline in {result['response_time_ms']}ms"
        )
        return result

    except Exception as e:
        end_time = time.perf_counter()
        error_time = int((end_time - start_time) * 1000)
        logger.error(
            f"[{trace_id}] Pipeline {pipeline_id} failed after {error_time}ms: {e}"
        )
        raise


# [PocketFlow] cache_helpers
def _cache_key(payload: dict) -> str:
    # make a stable key from important request params
    key_src = repr({
        "prompt": payload.get("prompt"),
        "models": payload.get("models"),
        "traits": payload.get("traits"),
    })
    return "cache:" + hashlib.sha256(key_src.encode("utf-8")).hexdigest()



# [PocketFlow] cache-set
try:
    if _pf_redis and 'ck' in locals() and 'response' in locals():
        _pf_redis.setex(ck, getattr(settings, "CACHE_TTL", 600), json.dumps(response))
except Exception:
    pass

