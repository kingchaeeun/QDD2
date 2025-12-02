"""
Lazy-loading model accessors.
Loading happens once per process to keep import time fast in downstream scripts.
"""

from functools import lru_cache
from typing import Tuple

import torch
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from transformers import MarianMTModel, MarianTokenizer, pipeline

from qdd2 import config


def _resolve_device(device: int) -> int:
    """
    Transformers pipeline uses -1 for CPU. Map GPU index if available, else fall back to -1.
    """
    if device is None:
        return -1
    if device >= 0 and not torch.cuda.is_available():
        return -1
    return device


@lru_cache(maxsize=4)
def get_ner_pipeline(device: int = config.DEFAULT_DEVICE):
    """Load the NER pipeline once; device is GPU index, falls back to CPU when unavailable."""
    resolved = _resolve_device(device)
    return pipeline(
        "ner",
        model=config.NER_MODEL_NAME,
        tokenizer=config.NER_MODEL_NAME,
        device=resolved,
    )


@lru_cache(maxsize=1)
def get_keyword_model() -> KeyBERT:
    """Shared KeyBERT model (Korean SBERT backbone)."""
    return KeyBERT(config.KEYBERT_MODEL_NAME)


@lru_cache(maxsize=1)
def get_translation_models() -> Tuple[MarianTokenizer, MarianMTModel]:
    """Tokenzier + model for Korean -> English translation."""
    tokenizer = MarianTokenizer.from_pretrained(config.TRANSLATION_MODEL_NAME)
    model = MarianMTModel.from_pretrained(config.TRANSLATION_MODEL_NAME)
    return tokenizer, model


@lru_cache(maxsize=1)
def get_sentence_model() -> SentenceTransformer:
    """SentenceTransformer for semantic similarity."""
    return SentenceTransformer(config.SENTENCE_MODEL_NAME)
