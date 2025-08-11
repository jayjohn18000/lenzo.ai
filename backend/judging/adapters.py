from typing import Optional, Dict, Any, Tuple
import json, re

LabelToScore = {
    "correct": 10.0, "mostly_correct": 8.0, "partially_correct": 6.0,
    "mixed": 5.0, "uncertain": 4.0, "hallucinated": 2.0, "incorrect": 0.0
}

def parse_json_maybe(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    # try direct json
    try:
        return json.loads(text)
    except Exception:
        pass
    # try find json block
    m = re.search(r'\{.*\}', text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def extract_numeric_score(text: str) -> Optional[float]:
    # prefer 0-10
    m = re.search(r'(?<!\d)(10(?:\.0)?|[0-9](?:\.[0-9])?)(?!\d)', text)
    if not m: 
        return None
    try:
        val = float(m.group(1))
        return max(0.0, min(10.0, val))
    except Exception:
        return None

def map_label_to_score(label: Optional[str]) -> Optional[float]:
    if not label: return None
    key = re.sub(r'[^a-z]+','_',label.lower()).strip('_')
    return LabelToScore.get(key)

def normalize(score_0_10: float) -> float:
    return max(0.0, min(1.0, score_0_10 / 10.0))

def parse_judge_output(raw: str) -> Tuple[Optional[float], Optional[str], str]:
    """
    Returns (score_0_1, label, reasons_text)
    """
    data = parse_json_maybe(raw)
    if data:
        score = data.get("score")
        label = data.get("label")
        reasons = data.get("reasons") or data.get("explanation") or raw
        if score is None:
            score = map_label_to_score(label)
        if isinstance(score, (int, float)):
            return normalize(float(score)), label, reasons
    # fallback: regex number
    num = extract_numeric_score(raw)
    if num is not None:
        return normalize(num), None, raw
    # fallback: map label keywords
    for k in LabelToScore.keys():
        if k.replace("_"," ") in raw.lower():
            mapped = map_label_to_score(k)
            return normalize(mapped), k, raw
    # nothing numeric -> vote only
    return None, None, raw
