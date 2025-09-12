# pocketflow/nodes/cursor_request_fix.py
import os, json, time
from pocketflow.store import SharedStore

ASK = """\
You are Cursor acting as code reviewer/fixer.

Context:
- Ticket: {title}
- Type: {ttype}
- Slug: {slug}
- Acceptance: {accept}
- Failure summary: {failure}

Task:
Generate a minimal UNIFIED DIFF (git-style) to fix the issue.
Target repo root is the workspace root. Do NOT include binary files.

Output instructions:
Save the diff as: pocketflow/patches/{slug}.diff
"""


def _slugify(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


class CursorRequestFix:
    name = "cursor_request_fix"

    def run(self, store: SharedStore) -> None:
        # get ticket with defaults to avoid KeyError
        t = store.context.get("ticket") or {}
        title = (t.get("title") or "untitled").strip()
        ttype = (t.get("type") or "unknown").strip()
        # slug fallback ensures non-empty value
        slug = _slugify(title) or str(int(time.time()))

        # failure bundle
        failure = {
            "tests": store.context.get("tests"),
            "smoke": store.context.get("smoke"),
        }

        # ensure tasks dir exists
        tasks_dir = os.path.join(store.repo_root, ".cursor", "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        bundle_path = os.path.join(tasks_dir, f"{slug}.md")

        # write task file for Cursor
        with open(bundle_path, "w", encoding="utf-8") as f:
            f.write(
                ASK.format(
                    title=title,
                    ttype=ttype,
                    slug=slug,
                    accept=json.dumps(t.get("acceptance", []), indent=2),
                    failure=json.dumps(failure, indent=2),
                )
            )

        # record in context
        store.context["cursor.task"] = {"path": bundle_path, "slug": slug}
