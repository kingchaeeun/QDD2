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

from quote_backend.config import (
    DEFAULT_DEVICE,
    KEYBERT_MODEL_NAME,
    NER_MODEL_NAME,
    SENTENCE_MODEL_NAME,
    TRANSLATION_MODEL_NAME,
)


def _resolve_device(device: int) -> int:
    """
    Transformers pipeline uses -1 for CPU. Map GPU index if available, else fall back to -1.
    
    Args:
        device: Device index (0 for CPU, >0 for GPU)
        
    Returns:
        Resolved device index for transformers pipeline
    """
    if device is None:
        return -1
    if device >= 0 and not torch.cuda.is_available():
        return -1
    return device


@lru_cache(maxsize=4)
def get_ner_pipeline(device: int = DEFAULT_DEVICE):
    """
    Load the NER pipeline once; device is GPU index, falls back to CPU when unavailable.
    
    Args:
        device: Device index (0 for CPU, >0 for GPU)
        
    Returns:
        NER pipeline instance
    """
    resolved = _resolve_device(device)
    return pipeline(
        "ner",
        model=NER_MODEL_NAME,
        tokenizer=NER_MODEL_NAME,
        device=resolved,
    )


@lru_cache(maxsize=1)
def get_keyword_model() -> KeyBERT:
    """
    Shared KeyBERT model (Korean SBERT backbone).
    
    Returns:
        KeyBERT model instance
    """
    return KeyBERT(KEYBERT_MODEL_NAME)


@lru_cache(maxsize=1)
def get_translation_models() -> Tuple[MarianTokenizer, MarianMTModel]:
    """
    Tokenizer + model for Korean -> English translation.
    
    Returns:
        Tuple of (tokenizer, model)
    """
    tokenizer = MarianTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
    model = MarianMTModel.from_pretrained(TRANSLATION_MODEL_NAME)
    return tokenizer, model


@lru_cache(maxsize=1)
def get_sentence_model() -> SentenceTransformer:
    """
    SentenceTransformer for semantic similarity.
    
    Returns:
        SentenceTransformer model instance
    """
    return SentenceTransformer(SENTENCE_MODEL_NAME)

