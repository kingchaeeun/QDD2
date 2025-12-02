"""
QDD2 modular package.

This package exposes reusable building blocks for:
- text normalization and sentence/quote utilities
- NER-driven keyword extraction
- person-name resolution (Wikidata + translation fallback)
- search/candidate collection and snippet span matching
- search query construction
"""

from app.entities import extract_ner_entities
from app.keywords import extract_keywords_with_ner
from app.translation import translate_ko_to_en
from app.name_resolution import resolve_person_name_en, get_wikidata_english_name
from app.query_builder import generate_search_query

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "translate_ko_to_en",
    "resolve_person_name_en",
    "get_wikidata_english_name",
    "generate_search_query",
]
