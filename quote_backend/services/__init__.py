"""
Service layer for quote extraction, search, and distortion detection.
"""

from quote_backend.services.quote_service import QuoteService
from quote_backend.services.search_service import SearchService

__all__ = [
    "QuoteService",
    "SearchService",
]

