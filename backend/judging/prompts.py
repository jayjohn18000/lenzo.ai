JUDGE_SYSTEM = """You are a strict evaluator. Return STRICT JSON:
{"score": <number 0-10>, "label": "<correct|mostly_correct|partially_correct|mixed|uncertain|hallucinated|incorrect>", "reasons": "<one short paragraph>"}"""

def judge_prompt(user_prompt: str, candidate_answer: str) -> str:
    return f"""Evaluate answer quality for the original user prompt.

USER PROMPT:
{user_prompt}

CANDIDATE ANSWER:
{candidate_answer}

Return STRICT JSON only, no extra text."""
