"""
Lightweight text helpers: cleaning, normalization, sentence splitting, and quote extraction.
"""

import re
from typing import Iterable, List


def clean_text(text: str) -> str:
    """
    Collapse whitespace and trim.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_korean_phrase(text: str) -> str:
    """
    Normalize by removing separators/whitespace and lowering.
    Useful for duplicate detection across variant spellings.
    
    Args:
        text: Korean phrase to normalize
        
    Returns:
        Normalized lowercase text without separators
    """
    if text is None:
        return ""
    normalized = re.sub(r"[·‧ㆍ\\-_/\\s]", "", text)
    return normalized.lower()


def split_sentences(text: str) -> List[str]:
    """
    Basic sentence segmentation that works reasonably for Korean/English mixed text.
    
    Args:
        text: Input text to split
        
    Returns:
        List of sentences
    """
    text = clean_text(text)
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+(?=[가-힣A-Za-z])", text)


def extract_quotes(text: str) -> List[str]:
    """
    Extract text inside double quotes.
    
    Args:
        text: Input text containing quotes
        
    Returns:
        List of quoted strings
    """
    return re.findall(r'"([^"]+)"', text or "")


def extract_quotes_advanced(text: str, min_length: int = 6) -> List[str]:
    """
    Extract quoted text using several quote styles, drop short/duplicate snippets.
    
    Args:
        text: Input text containing quotes
        min_length: Minimum length for a quote to be included
        
    Returns:
        List of unique quoted strings
    """
    text = text or ""
    # Support multiple quote styles (curly and straight, single and double)
    patterns = [
        r"“([^”]+)”",   # curly double quotes
        r'"([^"]+)"',   # straight double quotes
        r"'([^']+)'",   # straight single quotes
        r"‘([^’]+)’",   # curly single quotes
    ]

    quotes: List[str] = []
    for pattern in patterns:
        quotes.extend(re.findall(pattern, text))

    # Filter and deduplicate while preserving order
    seen = set()
    unique_quotes = []
    for q in quotes:
        cleaned = q.strip()
        if len(cleaned) < min_length or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_quotes.append(cleaned)

    return unique_quotes


def contains_korean(text: str) -> bool:
    """
    Return True if the text contains Korean characters.
    
    Args:
        text: Input text to check
        
    Returns:
        True if Korean characters are found
    """
    return bool(re.search(r"[가-힣]", text or ""))


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """
    Remove duplicates while keeping original order.
    
    Args:
        items: Iterable of strings
        
    Returns:
        List of unique strings in original order
    """
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

