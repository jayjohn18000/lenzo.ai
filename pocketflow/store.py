# pocketflow/store.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import os, json


@dataclass
class SharedStore:
    repo_root: str = field(
        default_factory=lambda: os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
    )
    env: Dict[str, str] = field(default_factory=lambda: dict(os.environ))
    context: Dict[str, Any] = field(default_factory=dict)  # plan, diffs, metrics, etc.

    def save(self, path: str = None) -> None:
        path = path or os.path.join(os.path.dirname(__file__), "store.snapshot.json")
        with open(path, "w") as f:
            json.dump(
                {"repo_root": self.repo_root, "env": self.env, "context": self.context},
                f,
                indent=2,
            )
