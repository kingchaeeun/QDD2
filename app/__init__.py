"""
Compatibility wrapper for app package.

This module provides backward compatibility by re-exporting functions
from the new quote_backend package structure.
"""

<<<<<<< HEAD:app/__init__.py
from app.entities import extract_ner_entities
from app.keywords import extract_keywords_with_ner
from app.translation import translate_ko_to_en
from app.name_resolution import resolve_person_name_en, get_wikidata_english_name
from app.query_builder import generate_search_query
=======
# Re-export from new structure
from quote_backend.core import (
    build_queries_from_text,
    extract_keywords_with_ner,
    extract_ner_entities,
    generate_search_query,
)
from quote_backend.utils import translate_ko_to_en
>>>>>>> main:app/__init__.py

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "translate_ko_to_en",
    "generate_search_query",
    "build_queries_from_text",
]
