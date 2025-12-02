"""
Shared quote extraction utilities exposed for both backend and extension layers.
"""

from .quote_extraction import extract_quotes, normalize_quote

__all__ = ["extract_quotes", "normalize_quote"]
