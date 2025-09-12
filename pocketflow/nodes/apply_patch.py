# pocketflow/nodes/apply_patch.py
import glob, os
from pocketflow.store import SharedStore
from pocketflow.utils import run


class ApplyPatch:
    name = "apply_patch"

    def run(self, store: SharedStore) -> None:
        patches_dir = os.path.join(store.repo_root, "pocketflow", "patches")
        os.makedirs(patches_dir, exist_ok=True)
        diffs = sorted(glob.glob(os.path.join(patches_dir, "*.diff")))
        if not diffs:
            store.context["patch"] = {"applied": False, "reason": "no diff files found"}
            return
        # apply the last diff
        diff = diffs[-1]
        # dry-run first (optional), then apply
        try:
            run(f"git apply --check '{diff}'", cwd=store.repo_root, check=True)
            run(f"git apply '{diff}'", cwd=store.repo_root, check=True)
            store.context["patch"] = {"applied": True, "file": diff}
        except Exception as e:
            store.context["patch"] = {"applied": False, "file": diff, "error": str(e)}
            # leave it for manual review
