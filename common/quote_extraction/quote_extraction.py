"""
Python-side quote extraction helpers shared by the FastAPI backend and any CLI tools.
This wraps the existing text utilities from app/text_utils.py so callers can import
from common.quote_extraction without depending on the app module layout.
"""

from typing import List

from app.text_utils import clean_text, extract_quotes_advanced


def normalize_quote(text: str | None) -> str:
  """Normalize whitespace and trim."""
  return clean_text(text or "")


def extract_quotes(text: str, min_length: int = 6) -> List[str]:
  """
  Extract quotes using the same regex set as the JS client, filtering by min_length.
  """
  return extract_quotes_advanced(text=text, min_length=min_length)
