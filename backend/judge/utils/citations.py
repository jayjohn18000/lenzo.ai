# backend/judge/utils/citations.py
"""
Citation extraction and management utilities
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse

def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    Extract citations and URLs from text
    """
    citations = []
    
    # Extract URLs using regex
    url_pattern = r'https?://[^\s<>"{}|\\^`[\]]*'
    urls = re.findall(url_pattern, text)
    
    for i, url in enumerate(urls):
        # Parse URL to get domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            citations.append({
                "id": f"url_{i+1}",
                "type": "url",
                "url": url,
                "domain": domain,
                "title": f"Reference from {domain}",
                "snippet": _extract_context_around_url(text, url)
            })
        except Exception:
            # Skip malformed URLs
            continue
    
    # Extract markdown-style citations [1], [2], etc.
    citation_pattern = r'\[(\d+)\]'
    citation_refs = re.findall(citation_pattern, text)
    
    for ref in citation_refs:
        citations.append({
            "id": f"ref_{ref}",
            "type": "reference",
            "number": ref,
            "title": f"Reference {ref}",
            "snippet": _extract_context_around_citation(text, f"[{ref}]")
        })
    
    return citations

def _extract_context_around_url(text: str, url: str, context_length: int = 100) -> str:
    """Extract text context around a URL"""
    url_pos = text.find(url)
    if url_pos == -1:
        return ""
    
    start = max(0, url_pos - context_length)
    end = min(len(text), url_pos + len(url) + context_length)
    
    context = text[start:end]
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."
    
    return context.strip()

def _extract_context_around_citation(text: str, citation: str, context_length: int = 100) -> str:
    """Extract text context around a citation reference"""
    citation_pos = text.find(citation)
    if citation_pos == -1:
        return ""
    
    start = max(0, citation_pos - context_length)
    end = min(len(text), citation_pos + len(citation) + context_length)
    
    context = text[start:end]
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."
    
    return context.strip()

def validate_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean up citations list
    """
    validated = []
    
    for citation in citations:
        # Basic validation
        if not citation.get("id") or not citation.get("type"):
            continue
        
        # Clean up URL citations
        if citation["type"] == "url":
            url = citation.get("url", "")
            if url.startswith(("http://", "https://")):
                validated.append(citation)
        else:
            validated.append(citation)
    
    return validated