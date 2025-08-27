# backend/judge/utils/citations.py
"""
Citation extraction and management utilities
"""

import re
from typing import List, Dict, Any, Tuple
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

def inject_citations(text: str, citations: List[Dict[str, Any]], format_style: str = "numbered") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Inject citations into text and return formatted text with citation list
    
    Args:
        text: The text to inject citations into
        citations: List of citation dictionaries
        format_style: Citation format - "numbered", "inline", or "footnote"
    
    Returns:
        Tuple of (formatted_text, formatted_citations)
    """
    if not citations:
        return text, []
    
    formatted_text = text
    formatted_citations = []
    
    if format_style == "numbered":
        # Add numbered citations [1], [2], etc.
        for i, citation in enumerate(citations, 1):
            citation_marker = f"[{i}]"
            
            # Create formatted citation entry
            formatted_citation = {
                "id": citation.get("id", f"cite_{i}"),
                "number": i,
                "type": citation.get("type", "reference"),
                "title": citation.get("title", f"Reference {i}"),
                "url": citation.get("url", ""),
                "domain": citation.get("domain", ""),
                "snippet": citation.get("snippet", "")
            }
            
            formatted_citations.append(formatted_citation)
            
            # If this citation has a URL, replace the URL in text with numbered reference
            if citation.get("url"):
                url = citation["url"]
                if url in formatted_text:
                    formatted_text = formatted_text.replace(url, citation_marker, 1)
    
    elif format_style == "inline":
        # Add inline citations with domain names
        for citation in citations:
            if citation.get("url"):
                url = citation["url"]
                domain = citation.get("domain", "source")
                inline_citation = f"({domain})"
                
                if url in formatted_text:
                    formatted_text = formatted_text.replace(url, inline_citation, 1)
                    formatted_citations.append({
                        "id": citation.get("id"),
                        "type": "inline",
                        "domain": domain,
                        "url": url,
                        "title": citation.get("title", f"Reference from {domain}")
                    })
    
    elif format_style == "footnote":
        # Add footnote-style citations
        footnote_text = "\n\n**References:**\n"
        for i, citation in enumerate(citations, 1):
            formatted_citation = {
                "id": citation.get("id", f"footnote_{i}"),
                "number": i,
                "type": "footnote",
                "title": citation.get("title", f"Reference {i}"),
                "url": citation.get("url", ""),
                "domain": citation.get("domain", "")
            }
            formatted_citations.append(formatted_citation)
            
            # Create footnote entry
            if citation.get("url"):
                footnote_text += f"{i}. {citation.get('title', 'Reference')}: {citation['url']}\n"
                # Replace URL in text with superscript number
                if citation["url"] in formatted_text:
                    formatted_text = formatted_text.replace(citation["url"], f"^{i}", 1)
        
        formatted_text += footnote_text
    
    return formatted_text, formatted_citations

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

def format_citation_list(citations: List[Dict[str, Any]], style: str = "numbered") -> str:
    """
    Format a list of citations for display
    
    Args:
        citations: List of citation dictionaries
        style: Format style - "numbered", "bullet", or "plain"
    
    Returns:
        Formatted citation list as string
    """
    if not citations:
        return ""
    
    formatted_lines = []
    
    for i, citation in enumerate(citations, 1):
        title = citation.get("title", f"Reference {i}")
        url = citation.get("url", "")
        domain = citation.get("domain", "")
        
        if style == "numbered":
            if url:
                line = f"{i}. {title} - {url}"
            else:
                line = f"{i}. {title}"
        elif style == "bullet":
            if url:
                line = f"• {title} - {url}"
            else:
                line = f"• {title}"
        else:  # plain
            if url:
                line = f"{title}: {url}"
            else:
                line = title
        
        formatted_lines.append(line)
    
    return "\n".join(formatted_lines)