"""
Compatibility wrapper for person-name resolution.
"""

from app.name_resolution import get_wikidata_english_name, resolve_person_name_en

__all__ = ["get_wikidata_english_name", "resolve_person_name_en"]
