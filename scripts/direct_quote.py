"""
Compatibility wrapper for quote utilities.
Prefer importing from app.text_utils and app.snippet_matcher directly in new code.
"""

from typing import List, Tuple

from app.snippet_matcher import extract_span
from app.text_utils import extract_quotes_advanced, split_sentences


__all__ = ["split_sentences", "extract_quotes_advanced", "extract_span"]
