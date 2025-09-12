# pocketflow/nodes/cursor_sync_rules.py
import os
from pocketflow.store import SharedStore

MASTER_RULES = """\
NextAGI Implementation Rules (PocketFlow + Cursor)

Goal: Implement auth on /api/v1/query, add per-key rate limiting, enable Redis caching with metrics.
Constraints: Security first (401 on missing/invalid key), deterministic tests, no secret leakage, idempotent migrations.
Style: Minimal diffs; docstrings on new functions; fast unit tests.

When I paste a PocketFlow failure bundle, propose a unified diff patch (git-style). Avoid mass refactors.
"""


class CursorSyncRules:
    name = "cursor_sync_rules"

    def run(self, store: SharedStore) -> None:
        rules_path = os.path.join(store.repo_root, ".cursor", "rules")
        os.makedirs(os.path.dirname(rules_path), exist_ok=True)
        if os.path.exists(rules_path):
            with open(rules_path, "a", encoding="utf-8") as f:
                f.write("\n\n# --- PocketFlow update ---\n" + MASTER_RULES + "\n")
        else:
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write(MASTER_RULES + "\n")
        store.context["cursor.rules"] = {"path": rules_path}
