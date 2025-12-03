"""
Service for quote extraction and processing.
"""

import logging
from typing import List, Optional

from quote_backend.core.pipeline import build_queries_from_text
from quote_backend.utils.text_utils import extract_quotes, extract_quotes_advanced

logger = logging.getLogger(__name__)


class QuoteService:
    """
    Service for extracting and processing quotes from text.
    """

    @staticmethod
    def extract_quotes(text: str, advanced: bool = True, min_length: int = 6) -> List[str]:
        """
        Extract quotes from text.
        
        Args:
            text: Input text
            advanced: Use advanced extraction (multiple quote styles)
            min_length: Minimum quote length
            
        Returns:
            List of extracted quotes
        """
        if advanced:
            return extract_quotes_advanced(text, min_length=min_length)
        return extract_quotes(text)

    @staticmethod
    def process_article(
        text: str,
        quote: Optional[str] = None,
        date: Optional[str] = None,
        top_n: int = 15,
        top_k: int = 3,
        rollcall: bool = False,
        device: int = 0,
        debug: bool = False,
    ) -> dict:
        """
        Process an article to extract entities, keywords, and generate search queries.
        
        Args:
            text: Article text
            quote: Optional specific quote sentence
            date: Optional article date (YYYY-MM-DD)
            top_n: Number of keywords to extract
            top_k: Number of keywords for query
            rollcall: Use rollcall mode
            device: Device index (0 for CPU, >0 for GPU)
            debug: Enable debug output
            
        Returns:
            Dictionary with pipeline results
        """
        return build_queries_from_text(
            text=text,
            top_n_keywords=top_n,
            top_k_for_query=top_k,
            quote_sentence=quote,
            article_date=date,
            rollcall_mode=rollcall,
            device=device,
            debug=debug,
        )

