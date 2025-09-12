# pocketflow/nodes/apply_edits.py
from pocketflow.store import SharedStore
from pocketflow.utils import (
    file_exists,
    ensure_import,
    ensure_text_block,
    replace_in_file,
)


class ApplyEdits:
    name = "apply_edits"

    def run(self, store: SharedStore) -> None:
        t = store.context["ticket"]
        ttype = t.get("type")
        if ttype == "enforce_api_key":
            self._enforce_api_key(store)
        elif ttype == "rate_limit":
            self._add_rate_limit(store)
        elif ttype == "enable_cache":
            self._enable_cache(store)
        else:
            raise ValueError(f"Unknown ticket type: {ttype}")

    # ---------- 1) enforce API key on /api/v1/query ----------
    def _enforce_api_key(self, store: SharedStore) -> None:
        paths = store.context["paths"]
        routes = paths["routes_v1"]
        auth_mod = paths["auth_api_key"]

        assert file_exists(routes), f"missing routes file: {routes}"
        assert file_exists(auth_mod), f"missing auth module: {auth_mod}"

        # 1) ensure import for Depends + verify_api_key
        ensure_import(routes, "from fastapi import Depends, HTTPException")
        ensure_import(routes, "from backend.auth.api_key import verify_api_key")

        # 2) add dependency to /api/v1/query handler
        # tries to match a FastAPI route function named query that takes RouteRequest
        replaced = replace_in_file(
            routes,
            r"(@router\.post\(\"/query\"[^\)]*\)\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\):)",
            r"\1",
        )
        # now inject Depends into the function signature if not present
        # add a kwarg: current_key=Depends(verify_api_key)
        add_dep = replace_in_file(
            routes,
            r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\):",
            lambda m: (
                f"def {m.group(1)}({m.group(2)}, current_key=Depends(verify_api_key)):"
                if "Depends(verify_api_key)" not in m.group(2)
                else m.group(0)
            ),
        )

        store.context["apply_edits.enforce_api_key"] = {
            "route_imports_added": True,
            "signature_patched": add_dep,
        }

    # ---------- 2) add per-key rate limiting (simple Redis-based middleware) ----------
    def _add_rate_limit(self, store: SharedStore) -> None:
        import os

        repo = store.repo_root
        main_py = store.context["paths"]["main"]
        limiter_path = os.path.join(repo, "backend", "middleware", "rate_limit.py")
        os.makedirs(os.path.dirname(limiter_path), exist_ok=True)

        # write a small middleware if not present
        if not file_exists(limiter_path):
            code = r"""# backend/middleware/rate_limit.py
import time
from typing import Callable
from fastapi import Request, Response
import redis

class RateLimiter:
    def __init__(self, redis_url: str, limit_per_minute: int = 60):
        self.r = redis.from_url(redis_url, decode_responses=True)
        self.limit = limit_per_minute

    async def __call__(self, request: Request, call_next: Callable):
        # Identify caller by API key (set by auth dependency) or IP fallback
        api_key = request.headers.get("authorization", "")
        key_id = api_key.split()[-1] if api_key else request.client.host
        window = int(time.time() // 60)
        counter_key = f"ratelimit:{key_id}:{window}"
        current = self.r.incr(counter_key)
        if current == 1:
            self.r.expire(counter_key, 65)
        if current > self.limit:
            return Response(status_code=429, content="Rate limit exceeded")
        return await call_next(request)
"""
            with open(limiter_path, "w", encoding="utf-8") as f:
                f.write(code)

        # ensure main.py mounts the middleware
        ensure_import(main_py, "from backend.middleware.rate_limit import RateLimiter")
        ensure_text_block(
            main_py,
            marker="# [PocketFlow] RateLimit mounted",
            block="""# [PocketFlow] RateLimit mounted
try:
    from backend.judge.config import settings
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    limit = int(getattr(settings, "RATE_LIMIT_PER_MINUTE", 60))
    app.middleware("http")(RateLimiter(redis_url, limit_per_minute=limit))
except Exception as e:
    import logging
    logging.warning(f"RateLimiter not mounted: {e}")
""",
        )
        store.context["apply_edits.rate_limit"] = {
            "middleware_file": limiter_path,
            "main_patched": True,
        }

    # ---------- 3) enable Redis caching with TTL + basic metrics ----------
    def _enable_cache(self, store: SharedStore) -> None:
        import os

        repo = store.repo_root
        # Common settings location mentioned: backend/judge/config.py
        settings_path = os.path.join(repo, "backend", "judge", "config.py")
        assert file_exists(settings_path), f"missing config at {settings_path}"

        # Flip default to True for ENABLE_CACHING, add TTL if missing
        replace_in_file(
            settings_path,
            r"(ENABLE_CACHING\s*:\s*bool\s*=\s*)False",
            r"\1True",
        )
        # add CACHE_TTL if not declared
        added_ttl = ensure_text_block(
            settings_path,
            marker="# [PocketFlow] CACHE_TTL",
            block="""# [PocketFlow] CACHE_TTL
try:
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "600"))
except Exception:
    CACHE_TTL = 600
""",
        )

        # Patch pipeline runner to read cache (best-effort: targets backend/judge/pipelines/runner.py)
        runner_path = os.path.join(repo, "backend", "judge", "pipelines", "runner.py")
        if file_exists(runner_path):
            ensure_import(runner_path, "import hashlib")
            ensure_import(runner_path, "from backend.judge.config import settings")
            ensure_import(runner_path, "import redis")
            ensure_text_block(
                runner_path,
                marker="# [PocketFlow] cache_helpers",
                block="""# [PocketFlow] cache_helpers
def _cache_key(payload: dict) -> str:
    # make a stable key from important request params
    key_src = repr({
        "prompt": payload.get("prompt"),
        "models": payload.get("models"),
        "traits": payload.get("traits"),
    })
    return "cache:" + hashlib.sha256(key_src.encode("utf-8")).hexdigest()
""",
            )
            # wrap run_pipeline entry/exit with cache get/set (conservative regex)
            replace_in_file(
                runner_path,
                r"def\s+run_pipeline\s*\((.*?)\):",
                lambda m: (
                    m.group(0)
                    if "# [PocketFlow] cache-wrap"
                    in open(runner_path, "r", encoding="utf-8").read()
                    else m.group(0)
                    + "\n    # [PocketFlow] cache-wrap\n    _pf_redis = None\n    if getattr(settings, 'ENABLE_CACHING', False):\n        try:\n            _pf_redis = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)\n            ck = _cache_key(locals().get('request') or locals().get('payload') or {})\n            if _pf_redis:\n                cached = _pf_redis.get(ck)\n                if cached:\n                    return json.loads(cached)\n        except Exception:\n            pass\n"
                ),
            )
            # append set-on-success near return points (best-effort: add at end)
            ensure_text_block(
                runner_path,
                marker="# [PocketFlow] cache-set",
                block="""# [PocketFlow] cache-set
try:
    if _pf_redis and 'ck' in locals() and 'response' in locals():
        _pf_redis.setex(ck, getattr(settings, "CACHE_TTL", 600), json.dumps(response))
except Exception:
    pass
""",
            )

        store.context["apply_edits.enable_cache"] = {
            "settings_patched": True,
            "runner_patched": file_exists(runner_path),
        }
