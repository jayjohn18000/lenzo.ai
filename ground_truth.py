# ground_truth.py
import os
from pathlib import Path
import json
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_FILE = BASE_DIR / "data" / "ground_truth.json"

def load_ground_truth() -> Dict[str, str]:
    if GROUND_TRUTH_FILE.exists():
        with open(GROUND_TRUTH_FILE, "r") as f:
            return json.load(f)
    return {}

def get_ground_truth(prompt: str) -> Optional[str]:
    ground_truths = load_ground_truth()
    return ground_truths.get(prompt)

def compare_to_ground_truth(response: str, ground_truth: str) -> int:
    """
    Returns 10 if response aligns with ground truth, 0 otherwise.
    In future, use semantic similarity scoring instead of exact match.
    """
    return 10 if ground_truth.lower() in response.lower() else 0
