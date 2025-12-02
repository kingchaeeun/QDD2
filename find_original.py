"""
Compatibility wrappers for the refactored app package.
Existing code can continue to import from find_original.py while the real logic lives in app/.
"""

from app.entities import extract_ner_entities
from app.keywords import extract_keywords_with_ner, rerank_with_ner_boost
from app.text_utils import extract_quotes, split_sentences, normalize_korean_phrase, clean_text
from app.translation import translate_ko_to_en

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "rerank_with_ner_boost",
    "extract_quotes",
    "split_sentences",
    "normalize_korean_phrase",
    "clean_text",
    "translate_ko_to_en",
]
