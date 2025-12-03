import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure repository root is importable (for app + common modules)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from common.quote_extraction import extract_quotes, normalize_quote  # noqa: E402
from app.pipeline import build_queries_from_text  # noqa: E402


app = FastAPI(title="app Backend", version="0.1.0")

ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "chrome-extension://*",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ArticlePayload(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    reporter: Optional[str] = None
    paragraphs: List[str] = []
    text: Optional[str] = None


class QuotePayload(BaseModel):
    id: Optional[int] = None
    text: str
    speaker: Optional[str] = None


class AnalyzeRequest(BaseModel):
    article: ArticlePayload
    quotes: Optional[List[QuotePayload]] = None


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> dict:
    article_text = payload.article.text or "\n".join(payload.article.paragraphs or [])
    quotes = payload.quotes or []

    quote_texts = [normalize_quote(q.text) for q in quotes if q.text and q.text.strip()]
    if not quote_texts and article_text:
        quote_texts = extract_quotes(article_text)

    results = []
    for index, quote_text in enumerate(quote_texts):
        pipeline_result = build_queries_from_text(
            text=article_text,
            top_n_keywords=15,
            top_k_for_query=3,
            quote_sentence=quote_text,
            article_date=None,
            rollcall_mode=False,
            device=0,
            debug=False,
        )

        results.append(
            {
                "id": quotes[index].id if index < len(quotes) and quotes[index].id is not None else index + 1,
                "text": quote_text,
                "speaker": quotes[index].speaker if index < len(quotes) else "Article quote",
                "sources": build_source_candidates(quote_text, pipeline_result),
            }
        )

    return {"quotes": results}


def build_source_candidates(quote_text: str, pipeline_result: dict) -> list[dict]:
    """
    Build lightweight source candidates using pipeline keywords/queries as stand-ins.
    This keeps the API shape that the extension UI expects until full search backends are wired.
    """
    keywords = pipeline_result.get("keywords") or []
    queries = pipeline_result.get("queries") or {}
    ko_query = queries.get("ko") or ""
    en_query = queries.get("en") or ""

    candidates = []
    for idx, kw in enumerate(keywords[:5]):
        keyword_value = kw[0] if isinstance(kw, (list, tuple)) and kw else kw
        distortion_score = 50 + ((idx * 11) % 45)
        similarity_score = 55 + ((idx * 7) % 40)

        candidates.append(
            {
                "id": idx + 1,
                "title": f"Keyword candidate: {keyword_value}",
                "sourceLink": f"https://search.example.com?q={en_query or ko_query}",
                "originalText": quote_text,
                "distortionScore": distortion_score,
                "similarityScore": similarity_score,
                "scores": {
                    "semanticReduction": distortion_score - 5,
                    "interpretiveExtension": distortion_score,
                    "lexicalColoring": distortion_score - 3,
                },
            }
        )

    if not candidates:
        candidates.append(
            {
                "id": 1,
                "title": "Auto-generated candidate",
                "sourceLink": f"https://search.example.com?q={en_query or ko_query or quote_text}",
                "originalText": quote_text,
                "distortionScore": 55,
                "similarityScore": 60,
                "scores": {
                    "semanticReduction": 50,
                    "interpretiveExtension": 55,
                    "lexicalColoring": 52,
                },
            }
        )

    return candidates
