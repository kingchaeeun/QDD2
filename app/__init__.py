"""
QDD2 modular package.

This package exposes reusable building blocks for:
- text normalization and sentence/quote utilities
- NER-driven keyword extraction
- person-name resolution (Wikidata + translation fallback)
- search/candidate collection and snippet span matching
- search query construction
"""

from qdd2.entities import extract_ner_entities
from qdd2.keywords import extract_keywords_with_ner
from qdd2.translation import translate_ko_to_en
from qdd2.name_resolution import resolve_person_name_en, get_wikidata_english_name
from qdd2.query_builder import generate_search_query

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "translate_ko_to_en",
    "resolve_person_name_en",
    "get_wikidata_english_name",
    "generate_search_query",
]
