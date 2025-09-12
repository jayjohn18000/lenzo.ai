# PocketFlow: NextAGI Implementation Flow

This folder provides a small automation flow to apply focused tickets:
1) Enforce API key auth on `/api/v1/query`
2) Add per-key rate limiting
3) Enable Redis caching with metrics

## Requirements
- Python 3.10+
- `pytest`, `black`, `ruff`, `uvicorn`, `httpx` (dev deps)
- Redis running for caching/rate-limit (if used)
- ENV: `OPENROUTER_API_KEY` (if your app needs it), `REDIS_URL` (if using Redis)

## Run a ticket
```bash
python pocketflow/flow.py --ticket pocketflow/tickets/001_enforce_api_key.yaml
