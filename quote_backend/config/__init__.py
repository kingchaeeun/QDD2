"""
Configuration module for quote backend.

Handles environment variables, model settings, and API configurations.
"""

import os
from typing import List, Set

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Model identifiers
NER_MODEL_NAME = "monologg/koelectra-base-v3-naver-ner"
KEYBERT_MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"
SENTENCE_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Device configuration: 0 = CPU, >0 for GPU (aligns with transformers pipeline)
DEFAULT_DEVICE = int(os.getenv("DEFAULT_DEVICE", "0"))

# Named-entity labels we keep from the NER model
NER_LABELS: Set[str] = {"PER", "ORG", "LOC", "DAT", "AFW"}

# Relation-like keywords to boost during keyword re-ranking (Korean terms)
RELATION_KEYWORDS: Set[str] = {
    "회담",
    "협력",
    "관계",
    "회의",
    "발표",
    "대화",
    "담화",
    "중재",
    "교섭",
    "협상",
    "동맹",
    "문제",
    "논란",
    "비판",
    "우려",
    "방침",
}

# Candidate collection defaults
BASE_DOMAINS: List[str] = [
    "site:whitehouse.gov",
    "site:congress.gov",
    "site:rollcall.com",
    "site:millercenter.org",
    "site:un.org",
    "site:factba.se",
    "site:foxnews.com",
    "site:c-span.org",
    "site:abcnews.go.com",
    "site:nbcnews.com",
    "site:cnn.com",
]

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuoteContextBot/1.0; +https://example.org/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

HTML_MIN_LENGTH = 500
DEFAULT_TIMEOUT = 12
PDF_TIMEOUT = 20

# Google API Configuration
# Prefer environment variables; fall back to legacy app.config values when present.
try:
    from app import config as legacy_app_config  # type: ignore
except Exception:
    legacy_app_config = None  # type: ignore[assignment]

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or (
    getattr(legacy_app_config, "GOOGLE_API_KEY_ENV", "") if legacy_app_config else ""
)
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX") or (
    getattr(legacy_app_config, "GOOGLE_CSE_CX_ENV", "") if legacy_app_config else ""
)

# API Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

