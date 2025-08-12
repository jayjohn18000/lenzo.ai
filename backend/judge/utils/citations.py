# backend/judge/utils/citations.py
import re
from typing import List, Dict, Any

# Very lightweight URL detector; good enough for MVP normalization
URL_RE = re.compile(r'https?://[^\s\)\]]+')

def extract_citations(text: str | None) -> List[Dict[str, Any]]:
    """
    Pull raw URLs from freeform text and normalize to a citations list.
    Used by the judge pipeline to keep citations "on" even when models inline links.
    """
    if not text:
        return []
    return [{"uri": u} for u in URL_RE.findall(text)]

def normalize_evidence_to_citations(evidence: List[dict] | None) -> List[Dict[str, Any]]:
    """
    Convert tool-chain evidence objects into a flat citations array.
    Keeps claim_id for traceability.
    """
    cites: List[Dict[str, Any]] = []
    for ev in evidence or []:
        claim_id = ev.get("claim_id")
        for s in ev.get("sources", []) or []:
            uri = s.get("uri") or s.get("url")
            if uri:
                cites.append({"uri": uri, "claim_id": claim_id})
    return cites
