#!/usr/bin/env bash
set -euo pipefail

FRONTEND="http://localhost:3000"
BACKEND="http://127.0.0.1:8000"

echo "=== Frontend Smoke ==="
for path in / /health /api/health /login /dashboard /status; do
  url="${FRONTEND}${path}"
  echo "GET $url"
  curl -sS -o /dev/null -w "  -> HTTP %{http_code} in %{time_total}s\n" "$url" || true
done

echo
echo "=== Backend Smoke ==="
for path in / /health /api/health /docs /redoc /openapi.json; do
  url="${BACKEND}${path}"
  echo "GET $url"
  curl -sS -o /dev/null -w "  -> HTTP %{http_code} in %{time_total}s\n" "$url" || true
done

echo
echo "Tip: If /openapi.json exists, use it to generate richer tests."
