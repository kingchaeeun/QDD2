"""
Translation utilities.
"""

import logging

from qdd2.models import get_translation_models

logger = logging.getLogger(__name__)


def translate_ko_to_en(text: str) -> str:
    """Translate Korean text to English using the Marian model."""
    tokenizer, model = get_translation_models()
    logger.debug("Translating text (len=%d): %s", len(text), text)
    tokens = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated = model.generate(**tokens)
    out = tokenizer.decode(translated[0], skip_special_tokens=True)
    logger.debug("Translation result: %s", out)
    return out

print(translate_ko_to_en("트럼프 베네수엘라 상공 전면폐쇄"))  # For quick test
