"""
Central configuration and constants.
Keep model names, label sets, and shared defaults here so they are easy to tweak.
"""

# Model identifiers
NER_MODEL_NAME = "monologg/koelectra-base-v3-naver-ner"
KEYBERT_MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"
SENTENCE_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Device configuration: 0 = CPU, >0 for GPU (aligns with transformers pipeline)
DEFAULT_DEVICE = 0

# Named-entity labels we keep from the NER model
NER_LABELS = {"PER", "ORG", "LOC", "DAT", "AFW"}

# Relation-like keywords to boost during keyword re-ranking (Korean terms)
RELATION_KEYWORDS = {
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
BASE_DOMAINS = [
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

GOOGLE_API_KEY_ENV = "AIzaSyD3Ll-FILhYzYO7wQjyIDcxIqc7YH56Uss"
GOOGLE_CSE_CX_ENV = "178e32d2f1d2b43bc"
