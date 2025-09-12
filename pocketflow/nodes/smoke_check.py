# pocketflow/nodes/smoke_check.py
import time, threading
from pocketflow.store import SharedStore
from pocketflow.utils import run
import httpx


class SmokeCheck:
    name = "smoke"

    def run(self, store: SharedStore) -> None:
        # start uvicorn in background
        def _serve():
            try:
                run(
                    "uvicorn backend.main:app --port 8001",
                    cwd=store.repo_root,
                    check=True,
                )
            except Exception:
                pass

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        time.sleep(1.5)  # give server time

        base = "http://127.0.0.1:8001"
        results = {}

        # unauthenticated
        try:
            r = httpx.post(
                f"{base}/api/v1/query",
                json={"prompt": "hello", "models": []},
                timeout=10,
            )
            results["unauth"] = {
                "status": r.status_code,
                "ok": r.status_code in (401, 403),
            }
        except Exception as e:
            results["unauth"] = {"error": str(e), "ok": False}

        # authenticated (if you have a dev key, set in env STORE or pass via header)
        headers = {}
        dev_key = store.env.get("DEV_API_KEY", "test_key_123")
        headers["Authorization"] = f"Bearer {dev_key}"
        try:
            r = httpx.post(
                f"{base}/api/v1/query",
                headers=headers,
                json={"prompt": "hello", "models": []},
                timeout=20,
            )
            results["auth"] = {
                "status": r.status_code,
                "ok": r.status_code in (200, 202, 429),
            }
        except Exception as e:
            results["auth"] = {"error": str(e), "ok": False}

        store.context["smoke"] = results
