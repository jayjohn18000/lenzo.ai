You are Cursor acting as code reviewer/fixer.

Context:
- Ticket: Enable Redis caching with TTL + basic metrics
- Type: enable_cache
- Slug: enable-redis-caching-with-ttl---basic-metrics
- Acceptance: [
  "ENABLE_CACHING default True in settings",
  "CACHE_TTL available from env or default",
  "Identical second request hits cache (lower latency)"
]
- Failure summary: {
  "tests": {
    "status": "failed",
    "error": "Command failed (1): pytest -q\n"
  },
  "smoke": {
    "unauth": {
      "error": "[Errno 61] Connection refused",
      "ok": false
    },
    "auth": {
      "error": "[Errno 61] Connection refused",
      "ok": false
    }
  }
}

Task:
Generate a minimal UNIFIED DIFF (git-style) to fix the issue.
Target repo root is the workspace root. Do NOT include binary files.

Output instructions:
Save the diff as: pocketflow/patches/enable-redis-caching-with-ttl---basic-metrics.diff
