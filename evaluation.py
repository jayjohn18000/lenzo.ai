# evaluation.py

from ground_truth import get_ground_truth, compare_to_ground_truth
from typing import Dict, List

def evaluate_factual_accuracy_with_ground_truth(prompt: str, responses: List[Dict[str, str]]) -> Dict[str, int]:
    """
    Evaluate factual accuracy of responses against known ground truth.
    Returns: {model_name: factual_score}
    """
    gt = get_ground_truth(prompt)
    if not gt:
        return {}  # No ground truth available

    result = {}
    for entry in responses:
        model = entry["model"]
        response = entry["response"]
        score = compare_to_ground_truth(response, gt)
        result[model] = score

    return result
