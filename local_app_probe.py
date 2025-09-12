#!/usr/bin/env python3
import time, json, sys, re
from urllib.parse import urljoin
import requests

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000"

TIMEOUT = 15

COMMON_FRONTEND_PATHS = [
    "/",
    "/health",
    "/api/health",
    "/login",
    "/dashboard",
    "/status",
]

COMMON_BACKEND_PATHS = [
    "/",
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]


def fetch(url, method="GET", **kwargs):
    t0 = time.time()
    try:
        r = requests.request(method, url, timeout=TIMEOUT, **kwargs)
        latency = (time.time() - t0) * 1000.0
        return {
            "url": url,
            "ok": r.ok,
            "status": r.status_code,
            "latency_ms": round(latency, 2),
            "headers": dict(r.headers),
            "text_sample": r.text[:500],
        }
    except Exception as e:
        latency = (time.time() - t0) * 1000.0
        return {
            "url": url,
            "ok": False,
            "status": None,
            "latency_ms": round(latency, 2),
            "error": str(e),
        }


def probe_frontend():
    results = []
    for path in COMMON_FRONTEND_PATHS:
        results.append(fetch(FRONTEND_URL.rstrip("/") + path))
    return results


def probe_backend_common():
    results = []
    for path in COMMON_BACKEND_PATHS:
        results.append(fetch(BACKEND_URL.rstrip("/") + path))
    return results


def parse_openapi():
    # Try to discover endpoints via OpenAPI
    url = BACKEND_URL.rstrip("/") + "/openapi.json"
    r = fetch(url)
    if not r.get("ok"):
        return r, []

    try:
        doc = json.loads(requests.get(url, timeout=TIMEOUT).text)
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e)}, []

    endpoints = []
    for path, path_item in doc.get("paths", {}).items():
        for method in path_item.keys():
            endpoints.append({"method": method.upper(), "path": path})
    return r, endpoints


def probe_backend_openapi(endpoints):
    results = []
    for ep in endpoints:
        url = BACKEND_URL.rstrip("/") + ep["path"]
        method = ep["method"]
        # For GET endpoints, we can safely try without body
        if method == "GET":
            results.append(fetch(url, method="GET"))
        # For POST endpoints with obvious test/echo paths, try minimal payload
        elif method == "POST" and re.search(
            r"(test|echo|health|status)", ep["path"], re.I
        ):
            results.append(fetch(url, method="POST", json={"ping": "pong"}))
        else:
            results.append(
                {
                    "url": url,
                    "method": method,
                    "skipped": True,
                    "reason": "Non-GET or unsafe to call without schema-aware payload",
                }
            )
    return results


def main():
    report = {
        "meta": {
            "frontend_base": FRONTEND_URL,
            "backend_base": BACKEND_URL,
        },
        "checks": {},
    }

    report["checks"]["frontend_common"] = probe_frontend()
    report["checks"]["backend_common"] = probe_backend_common()

    openapi_meta, endpoints = parse_openapi()
    report["checks"]["backend_openapi_meta"] = openapi_meta
    report["checks"]["backend_endpoints_discovered"] = endpoints

    if endpoints:
        report["checks"]["backend_openapi_probing"] = probe_backend_openapi(endpoints)

    # Save JSON report
    with open("local_app_probe_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Wrote local_app_probe_report.json")
    print(
        json.dumps(
            {
                "summary": {
                    "frontend_ok": any(
                        c.get("ok") for c in report["checks"]["frontend_common"]
                    ),
                    "backend_ok": any(
                        c.get("ok") for c in report["checks"]["backend_common"]
                    ),
                    "endpoints_discovered": len(endpoints),
                }
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
