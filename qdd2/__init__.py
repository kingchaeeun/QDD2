"""
Compatibility wrapper for qdd2 package.

This module provides backward compatibility by re-exporting functions
from the new quote_backend package structure.
"""

# Re-export from new structure
from quote_backend.core import (
    build_queries_from_text,
    extract_keywords_with_ner,
    extract_ner_entities,
    generate_search_query,
)
from quote_backend.utils import translate_ko_to_en

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "translate_ko_to_en",
    "generate_search_query",
    "build_queries_from_text",
]
