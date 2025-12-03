"""
Translation utilities for Korean to English translation.
"""

import logging

from quote_backend.models.loaders import get_translation_models

logger = logging.getLogger(__name__)


def translate_ko_to_en(text: str) -> str:
    """
    Translate Korean text to English using the Marian model.
    
    Args:
        text: Korean text to translate
        
    Returns:
        Translated English text
        
    Raises:
        Exception: If translation fails
    """
    tokenizer, model = get_translation_models()
    logger.debug("Translating text (len=%d): %s", len(text), text)
    tokens = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated = model.generate(**tokens)
    out = tokenizer.decode(translated[0], skip_special_tokens=True)
    logger.debug("Translation result: %s", out)
    return out

