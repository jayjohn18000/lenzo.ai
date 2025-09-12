You are Cursor acting as code reviewer/fixer.

Context:
- Ticket: Secure /api/v1/query with API key
- Type: enforce_api_key
- Slug: secure--api-v1-query-with-api-key
- Acceptance: [
  "Unauthenticated POST /api/v1/query returns 401 or 403",
  {
    "Authenticated request (Authorization": "Bearer <key>) returns 200/202 or 429"
  }
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
Save the diff as: pocketflow/patches/secure--api-v1-query-with-api-key.diff
