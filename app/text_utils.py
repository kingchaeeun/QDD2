"""
Lightweight text helpers: cleaning, normalization, sentence splitting, and quote extraction.
"""

import re
from typing import Iterable, List


def clean_text(text: str) -> str:
    """Collapse whitespace and trim."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_korean_phrase(text: str) -> str:
    """
    Normalize by removing separators/whitespace and lowering.
    Useful for duplicate detection across variant spellings.
    """
    if text is None:
        return ""
    normalized = re.sub(r"[·‧ㆍ\\-_/\\s]", "", text)
    return normalized.lower()


def split_sentences(text: str) -> List[str]:
    """
    Basic sentence segmentation that works reasonably for Korean/English mixed text.
    """
    text = clean_text(text)
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+(?=[가-힣A-Za-z])", text)


def extract_quotes(text: str) -> List[str]:
    """Extract text inside double quotes."""
    return re.findall(r'"([^"]+)"', text or "")


def extract_quotes_advanced(text: str, min_length: int = 6) -> List[str]:
    """
    Extract quoted text using several quote styles, drop short/duplicate snippets.
    """
    text = text or ""
    patterns = [
        r"“([^”]+)”",
        r'"([^"]+)"',
        r"'([^']+)'",
        r"‘([^’]+)’",
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
    """Return True if the text contains Korean characters."""
    return bool(re.search(r"[가-힣]", text or ""))


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Remove duplicates while keeping original order."""
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
