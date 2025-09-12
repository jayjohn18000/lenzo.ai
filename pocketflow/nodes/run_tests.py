# pocketflow/nodes/run_tests.py
from pocketflow.store import SharedStore
from pocketflow.utils import run


class RunTests:
    name = "tests"

    def run(self, store: SharedStore) -> None:
        # best effort: run pytest; tolerate missing tests but nudge user
        try:
            run("pytest -q", cwd=store.repo_root, check=True)
            store.context["tests"] = {"status": "passed"}
        except Exception as e:
            store.context["tests"] = {"status": "failed", "error": str(e)}
            # Don't hard-fail the whole flow; allow you to inspect
            # Raise if you want to stop:
            # raise
