# pocketflow/nodes/format_code.py
from pocketflow.store import SharedStore
from pocketflow.utils import run


class FormatCode:
    name = "format"

    def run(self, store: SharedStore) -> None:
        try:
            run("ruff --fix .", cwd=store.repo_root, check=False)
        except Exception:
            pass
        try:
            run("black .", cwd=store.repo_root, check=False)
        except Exception:
            pass
        store.context["format"] = {"done": True}
