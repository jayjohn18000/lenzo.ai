# pocketflow/flow.py
import argparse, time
from pocketflow.store import SharedStore
from pocketflow.nodes.cursor_sync_rules import CursorSyncRules
from pocketflow.nodes.plan_ticket import PlanTicket
from pocketflow.nodes.apply_edits import ApplyEditsFixed as ApplyEdits
from pocketflow.nodes.run_tests import RunTests
from pocketflow.nodes.format_code import FormatCode
from pocketflow.nodes.smoke_check import SmokeCheck
from pocketflow.nodes.cursor_request_fix import CursorRequestFix
from pocketflow.nodes.apply_patch import ApplyPatch


def tests_and_smoke_passed(store: SharedStore) -> bool:
    t = store.context.get("tests", {})
    s = store.context.get("smoke", {})
    tests_ok = t.get("status") == "passed"
    smoke = s or {}
    unauth_ok = smoke.get("unauth", {}).get("ok") is True
    auth_ok = smoke.get("auth", {}).get("ok") is True
    return tests_ok and unauth_ok and auth_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--max-iters", type=int, default=3)
    args = ap.parse_args()

    store = SharedStore()
    # One-time setup: ensure Cursor has rules
    ##  CursorSyncRules().run(store)

    # First pass: plan → apply → tests → format → smoke
    PlanTicket(args.ticket).run(store)
    ApplyEdits().run(store)
    RunTests().run(store)
    FormatCode().run(store)
    SmokeCheck().run(store)
    store.save()

    # Loop with Cursor-assisted fixes
    it = 0
    while not tests_and_smoke_passed(store) and it < args.max_iters:
        it += 1
        print(f"\n✳️  Iteration {it}: tests/smoke failed. Preparing Cursor task...")
        CursorRequestFix().run(store)
        task = store.context["cursor.task"]["path"]
        print(f"Open this in Cursor and ask it to produce a unified diff:\n  {task}")
        print("→ Save the diff as pocketflow/patches/<anything>.diff when ready.")
        # Simple wait loop. (You can press Ctrl+C and re-run later if you prefer.)
        for _ in range(60):  # wait up to ~60 seconds, or change strategy
            time.sleep(1)

        ApplyPatch().run(store)
        RunTests().run(store)
        FormatCode().run(store)
        SmokeCheck().run(store)
        store.save()

    print("\nDone. Summary:")
    for k, v in store.context.items():
        print(f"- {k}: {v}")
    if tests_and_smoke_passed(store):
        print("✅ All good!")
    else:
        print("⚠️ Still failing; check .cursor/tasks/ and pocketflow/patches/")


if __name__ == "__main__":
    main()
