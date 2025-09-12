You are Cursor acting as code reviewer/fixer.

Context:
- Ticket: Add per-key rate limiting
- Type: rate_limit
- Slug: add-per-key-rate-limiting
- Acceptance: [
  "Burst above limit yields HTTP 429",
  "Normal traffic unaffected"
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
Save the diff as: pocketflow/patches/add-per-key-rate-limiting.diff
