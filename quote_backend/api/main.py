"""
FastAPI application for quote detection backend.
"""

import hashlib
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.search_client import html_to_text
from bs4 import BeautifulSoup
from quote_backend.config import API_DEBUG, LOG_LEVEL
from quote_backend.core.query_builder import generate_search_query
from quote_backend.services.quote_service import QuoteService
from quote_backend.services.search_service import SearchService
from quote_backend.utils.translation import translate_ko_to_en
from quote_backend.utils.text_utils import extract_quotes_advanced

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Quote Detection Backend API",
    description="Backend API for detecting and analyzing quote distortions in news articles",
    version="1.0.0",
    debug=API_DEBUG,
)

# CORS middleware for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QuoteAnalysisRequest(BaseModel):
    """Request model for quote analysis."""
    
    text: str = Field(..., description="Article text to analyze")
    quote: Optional[str] = Field(None, description="Specific quote sentence (optional)")
    date: Optional[str] = Field(None, description="Article date (YYYY-MM-DD)")
    top_n: int = Field(15, description="Number of keywords to extract")
    top_k: int = Field(3, description="Number of keywords for query")
    rollcall: bool = Field(False, description="Use rollcall.com-oriented query")
    search: bool = Field(False, description="Run web search and find best match")
    device: int = Field(0, description="Device index (0 for CPU, >0 for GPU)")


class QuoteAnalysisResponse(BaseModel):
    """Response model for quote analysis."""
    
    pipeline_result: dict = Field(..., description="Pipeline extraction results")
    search_items: list = Field(default_factory=list, description="Search results")
    best_span: Optional[dict] = Field(None, description="Best matching span from sources")
    is_trump_context: bool = Field(False, description="Whether context is Trump-related")
    speaker_ko: Optional[str] = Field(None, description="Primary inferred speaker name in Korean")
    speaker_en: Optional[str] = Field(None, description="Primary inferred speaker name in English")


class QuoteExtractionRequest(BaseModel):
    """Request model for direct-quote extraction."""

    text: str = Field(..., description="Full article text (headline + body)")
    min_length: int = Field(6, ge=1, le=500, description="Minimum quote length to include")


class QuoteExtractionResponse(BaseModel):
    """Response model for direct-quote extraction."""

    quotes_ko: List[str] = Field(default_factory=list, description="Extracted Korean quotes")
    quotes_en: List[str] = Field(default_factory=list, description="Machine-translated English quotes")


class AnalyzeArticleRequest(BaseModel):
    """Request model for full-article HTML analysis."""

    article_html: str = Field(..., description="Raw article HTML content")
    article_date: Optional[str] = Field(
        None,
        description="Article date (YYYY-MM-DD), used for rollcall-friendly query generation",
    )


class QuoteCandidateResult(BaseModel):
    """Single (quote, candidate) pair for frontend mapping."""

    quote_id: int = Field(..., description="Sequential quote index within article (1-based)")
    article_quote: str = Field(..., description="Direct quote text extracted from article")
    candidate_id: str = Field(..., description="Stable candidate identifier (e.g., URL+span hash)")
    candidate_link: str = Field(..., description="URL of the source candidate")
    source_span: str = Field(..., description="Matched span text in the source")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity score (0–1)")
    distortion_score: float = Field(..., ge=0.0, le=1.0, description="Estimated distortion score (0–1)")


class AnalyzeArticleResponse(BaseModel):
    """Response model wrapping all (quote, candidate) mappings."""

    results: List[QuoteCandidateResult] = Field(default_factory=list)


class AnalyzeQuotesArticle(BaseModel):
    """Article metadata for quote-level analysis."""

    title: Optional[str] = Field(None, description="Article title")
    reporter: Optional[str] = Field(None, description="Reporter name")
    paragraphs: List[str] = Field(default_factory=list, description="Article body paragraphs")
    date: Optional[str] = Field(
        None,
        description="Article date (YYYY-MM-DD), used for rollcall-friendly query generation",
    )
    text: Optional[str] = Field(None, description="Full article text (headline + body)")
    url: Optional[str] = Field(None, description="Article URL (for reference only)")


class AnalyzeQuotesQuote(BaseModel):
    """Single detected quote coming from the Chrome extension."""

    id: int = Field(..., description="Stable quote identifier (1-based)")
    text: str = Field(..., description="Quote text extracted from the article")
    speaker: Optional[str] = Field(None, description="Inferred speaker name, if available")


class QuoteSourceScores(BaseModel):
    """Per-dimension distortion scores (0–100)."""

    semanticReduction: int = Field(..., ge=0, le=100)
    interpretiveExtension: int = Field(..., ge=0, le=100)
    lexicalColoring: int = Field(..., ge=0, le=100)


class QuoteSource(BaseModel):
    """Source candidate for a specific quote, shaped for the extension UI."""

    id: int = Field(..., description="Per-quote local source index (1-based)")
    title: str = Field(..., description="Human-readable source label")
    sourceLink: str = Field(..., description="Source URL")
    originalText: str = Field(..., description="Matched span text from the source")
    distortionScore: int = Field(..., ge=0, le=100, description="Overall distortion score (0–100)")
    similarityScore: int = Field(..., ge=0, le=100, description="Similarity score (0–100)")
    scores: QuoteSourceScores = Field(..., description="Per-dimension distortion scores")
    candidate_id: Optional[str] = Field(
        None,
        description="Backend candidate identifier (hash of URL+span) for stable mapping",
    )


class AnalyzedQuote(BaseModel):
    """Quote with attached source candidates for the extension UI."""

    id: int = Field(..., description="Quote identifier (mirrors input id)")
    text: str = Field(..., description="Quote text")
    speaker: str = Field(..., description="Speaker label for display")
    sources: List[QuoteSource] = Field(default_factory=list, description="Matched source candidates")


class AnalyzeQuotesRequest(BaseModel):
    """Request model for quote-level analysis used by the Chrome extension."""

    article: AnalyzeQuotesArticle = Field(..., description="Article metadata + text")
    quotes: List[AnalyzeQuotesQuote] = Field(..., description="Detected quotes from the content script")


class AnalyzeQuotesResponse(BaseModel):
    """Response model returning DetectedQuote-like payloads."""

    quotes: List[AnalyzedQuote] = Field(default_factory=list)


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Quote Detection Backend API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/analyze", response_model=QuoteAnalysisResponse)
async def analyze_quote(request: QuoteAnalysisRequest):
    """
    Analyze article text and optionally search for original sources.
    
    This endpoint:
    1. Extracts entities and keywords from the article
    2. Generates search queries (Korean/English)
    3. Optionally performs web search and finds best matching source
    """
    try:
        logger.info("Received analysis request: text_len=%d, quote=%s", len(request.text), bool(request.quote))
        
        # Step 1: Process article
        pipeline_result = QuoteService.process_article(
            text=request.text,
            quote=request.quote,
            date=request.date,
            top_n=request.top_n,
            top_k=request.top_k,
            rollcall=request.rollcall,
            device=request.device,
            debug=API_DEBUG,
        )
        
        # Step 2: Check for Trump context
        is_trump_context = _check_trump_context(pipeline_result, request.text, request.quote)

        # Step 2.5: Infer primary speaker from NER entities (PER)
        entities_by_type = pipeline_result.get("entities_by_type", {}) or {}
        per_list = entities_by_type.get("PER") or []
        speaker_ko: Optional[str] = per_list[0] if per_list else None
        speaker_en: Optional[str] = None
        if speaker_ko:
            try:
                speaker_en = translate_ko_to_en(speaker_ko)
            except Exception:
                speaker_en = speaker_ko
        
        # Step 3: Search if requested
        search_items = []
        best_span = None
        
        if request.search:
            logger.info("Running search with generated query")
            query = pipeline_result["queries"].get("en") or pipeline_result["queries"].get("ko")

            if query:
                # 트럼프 컨텍스트가 감지되면 rollcall 플래그와 무관하게
                # Rollcall 검색이 우선 사용되도록 한다.
                rollcall_flag = bool(request.rollcall or is_trump_context)

                search_items = SearchService.search(
                    query=query,
                    is_trump_context=is_trump_context,
                    rollcall=rollcall_flag,
                    num_results=5,
                    debug=API_DEBUG,
                )
                
                if search_items:
                    best_span = SearchService.find_best_match(
                        quote_text=request.quote or "",
                        search_items=search_items,
                        query_en=pipeline_result["queries"].get("en"),
                    )
            else:
                logger.warning("No query available to search.")
        
        return QuoteAnalysisResponse(
            pipeline_result=pipeline_result,
            search_items=search_items,
            best_span=best_span,
            is_trump_context=is_trump_context,
            speaker_ko=speaker_ko,
            speaker_en=speaker_en,
        )
        
    except Exception as e:
        logger.error("Error processing request: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/extract-quotes", response_model=QuoteExtractionResponse)
async def extract_quotes_endpoint(request: QuoteExtractionRequest) -> QuoteExtractionResponse:
    """
    Extract direct quotes from article text using the shared backend logic.

    This reuses `extract_quotes_advanced` from `quote_backend.utils.text_utils`
    (which is the same implementation used in the original app pipeline).
    """
    try:
        quotes_ko = extract_quotes_advanced(request.text, min_length=request.min_length) or []
        quotes_en: List[str] = []
        for q in quotes_ko:
            try:
                quotes_en.append(translate_ko_to_en(q))
            except Exception:
                # If translation fails, just reuse the original Korean text
                quotes_en.append(q)
        return QuoteExtractionResponse(quotes_ko=quotes_ko, quotes_en=quotes_en)
    except Exception as e:
        logger.error("Error extracting quotes", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_similarity(raw_score: float) -> float:
    """Map raw SBERT cosine similarity (-1..1) into normalized [0, 1] range."""
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    norm = (score + 1.0) / 2.0
    return max(0.0, min(1.0, norm))


def _estimate_distortion(similarity_score: float) -> float:
    """
    Lightweight distortion proxy based on similarity.

    Higher similarity ⇒ lower distortion. This keeps the API stable while
    allowing a dedicated distortion classifier to be plugged in later.
    """
    try:
        sim = float(similarity_score)
    except (TypeError, ValueError):
        return 0.0
    dist = 1.0 - sim
    return max(0.0, min(1.0, dist))


def _build_article_text(article: AnalyzeQuotesArticle) -> str:
    """
    Compose a full article text string from the request payload.

    Prefer explicit `text` if provided, otherwise join title + paragraphs.
    """
    if article.text and article.text.strip():
        return article.text

    parts: List[str] = []
    if article.title:
        parts.append(article.title)
    parts.extend(article.paragraphs or [])
    return "\n".join(p for p in parts if p).strip()


def _build_keyword_fallback_candidates_for_quote(
    quote_idx: int,
    quote_text: str,
    pipeline_result: dict,
) -> List[QuoteCandidateResult]:
    """
    Build lightweight, search-free candidates from pipeline keywords.

    This mirrors the original Node backend behavior so that we can still
    return meaningful results when Google CSE is not configured or returns
    no items.
    """
    keywords = pipeline_result.get("keywords") or []
    queries = pipeline_result.get("queries") or {}
    ko_query = queries.get("ko") or ""
    en_query = queries.get("en") or ""

    results: List[QuoteCandidateResult] = []
    if not keywords:
        return results

    for local_idx, kw in enumerate(keywords[:5], start=1):
        if isinstance(kw, (list, tuple)) and kw:
            keyword_value = str(kw[0])
        else:
            keyword_value = str(kw)

        # Simple synthetic similarity/distortion (closer keyword → higher sim)
        sim = max(0.0, min(1.0, 0.6 + 0.07 * (5 - local_idx)))  # ~0.88..0.60
        dist = _estimate_distortion(sim)

        raw_id = f"kw://{keyword_value}|quote={quote_idx}|rank={local_idx}"
        candidate_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:16]

        # Local search-style link; front-end treats it just as a URL string.
        query_part = en_query or ko_query or quote_text
        candidate_link = f"https://search.local?q={query_part}"

        results.append(
            QuoteCandidateResult(
                quote_id=quote_idx,
                article_quote=quote_text,
                candidate_id=candidate_id,
                candidate_link=candidate_link,
                source_span=keyword_value,
                similarity_score=sim,
                distortion_score=dist,
            )
        )

    return results


def _extract_article_date_from_html(html: str) -> Optional[str]:
    """
    Best-effort extraction of article date (YYYY-MM-DD) from raw HTML.

    This is primarily used to support rollcall-friendly query generation
    when the client does not provide an explicit article_date.
    """
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("BeautifulSoup failed while extracting article date: %s", exc)
        return None

    # 1) Common meta tag: <meta property="article:published_time" content="2025-08-26T07:20:00+09:00">
    meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find(
        "meta", attrs={"name": "article:published_time"}
    )
    content = None
    if meta and meta.get("content"):
        content = str(meta["content"]).strip()

    # 2) Fallback: look for data in JSON blobs that expose "article_date":"2025.08.26"
    if not content:
        for script in soup.find_all("script"):
            text = script.string or ""
            if "article_date" in text:
                # naive pattern search; sufficient for our controlled test fixtures
                import re as _re

                m = _re.search(r'"article_date"\s*:\s*"(.*?)"', text)
                if m:
                    content = m.group(1)
                    break

    if not content:
        return None

    # Normalize to YYYY-MM-DD
    content = content.strip()
    date_str = content[:10]
    # Accept formats like 2025-08-26 or 2025.08.26
    date_str = date_str.replace(".", "-").replace("/", "-")

    import re as _re

    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return None

    return date_str


@app.post("/analyze-article", response_model=AnalyzeArticleResponse)
async def analyze_article(request: AnalyzeArticleRequest) -> AnalyzeArticleResponse:
    """
    End-to-end article HTML analysis for the Chrome Extension.

    Pipeline:
      1) HTML → plain text
      2) Direct-quote extraction (quote_id assignment)
      3) For each quote:
           - reuse core pipeline to build search queries
           - run web search + snippet-level span matching
           - compute similarity/distortion scores per candidate
      4) Flatten to a single list of (quote_id, candidate) objects.
    """
    try:
        if not request.article_html or not request.article_html.strip():
            raise HTTPException(status_code=400, detail="article_html must not be empty")

        # 1) Normalize HTML to plain article text
        article_text = html_to_text(request.article_html or "")
        if not article_text:
            # Return an empty but well-formed payload to keep frontend logic simple
            return AnalyzeArticleResponse(results=[])

        # 1.5) Derive article_date if not provided explicitly
        article_date = request.article_date or _extract_article_date_from_html(request.article_html or "")

        # 2) Extract direct quotes and assign quote_ids (1-based)
        quotes_ko = extract_quotes_advanced(article_text, min_length=6) or []
        if not quotes_ko:
            return AnalyzeArticleResponse(results=[])

        all_results: List[QuoteCandidateResult] = []

        for quote_idx, quote_text in enumerate(quotes_ko, start=1):
            # 3a) Build pipeline context (entities/keywords/queries) for this quote
            pipeline_result = QuoteService.process_article(
                text=article_text,
                quote=quote_text,
                date=article_date,
                top_n=15,
                top_k=3,
                rollcall=False,
                device=0,
                debug=API_DEBUG,
            )

            is_trump_context = _check_trump_context(pipeline_result, article_text, quote_text)

            # Rollcall 모드일 경우, 동일한 extraction 결과를 사용해 쿼리만 재구성
            if is_trump_context and article_date:
                try:
                    rollcall_queries = generate_search_query(
                        entities_by_type=pipeline_result.get("entities_by_type", {}) or {},
                        keywords=pipeline_result.get("keywords", []) or [],
                        top_k=3,
                        quote_sentence=quote_text,
                        article_date=article_date,
                        rollcall_mode=True,
                        entities=pipeline_result.get("entities"),
                    )
                    pipeline_result["queries"] = rollcall_queries
                except Exception as e:
                    logger.warning("Rollcall query generation failed, falling back to default: %s", e)

            queries = pipeline_result.get("queries") or {}
            query_en = queries.get("en")
            query_ko = queries.get("ko")
            query = query_en or query_ko

            if not query:
                # No usable query → fall back to keyword-only candidates
                all_results.extend(
                    _build_keyword_fallback_candidates_for_quote(
                        quote_idx=quote_idx,
                        quote_text=quote_text,
                        pipeline_result=pipeline_result,
                    )
                )
                continue

            # 3b) Search + span matching (Rollcall 우선 + 도메인 우선순위 CSE)
            search_items = SearchService.search(
                query=query,
                is_trump_context=is_trump_context,
                rollcall=is_trump_context,
                num_results=5,
                debug=API_DEBUG,
            )

            if not search_items:
                # No external results → keyword-only fallback
                all_results.extend(
                    _build_keyword_fallback_candidates_for_quote(
                        quote_idx=quote_idx,
                        quote_text=quote_text,
                        pipeline_result=pipeline_result,
                    )
                )
                continue

            best_span = SearchService.find_best_match(
                quote_text=quote_text,
                search_items=search_items,
                query_en=query_en,
                min_score=0.0,
                num_before=1,
                num_after=1,
            )

            if not best_span:
                # Matching failed → keyword-only fallback
                all_results.extend(
                    _build_keyword_fallback_candidates_for_quote(
                        quote_idx=quote_idx,
                        quote_text=quote_text,
                        pipeline_result=pipeline_result,
                    )
                )
                continue

            # snippet_matcher attaches a full ranked list as "top_k_candidates"
            candidates = best_span.get("top_k_candidates") or [best_span]

            for cand in candidates:
                url = cand.get("url")
                span_text = cand.get("span_text") or cand.get("best_sentence") or ""
                if not url or not span_text:
                    continue

                raw_score = cand.get("best_score", 0.0)
                sim_score = _normalize_similarity(raw_score)
                dist_score = _estimate_distortion(sim_score)

                # Stable candidate_id based on URL + span_text
                raw_id = f"{url}|{span_text}"
                candidate_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:16]

                all_results.append(
                    QuoteCandidateResult(
                        quote_id=quote_idx,
                        article_quote=quote_text,
                        candidate_id=candidate_id,
                        candidate_link=url,
                        source_span=span_text,
                        similarity_score=sim_score,
                        distortion_score=dist_score,
                    )
                )

        return AnalyzeArticleResponse(results=all_results)

    except HTTPException:
        # Re-raise explicit HTTP errors without logging as 500
        raise
    except Exception as e:
        logger.error("Error in /analyze-article pipeline: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze-quotes", response_model=AnalyzeQuotesResponse)
async def analyze_quotes(request: AnalyzeQuotesRequest) -> AnalyzeQuotesResponse:
    """
    Quote-level analysis endpoint used by the Chrome extension.

    The content script sends:
      - Parsed article (title, paragraphs, text)
      - Direct quotes with stable ids

    This endpoint:
      - Reuses the core pipeline for each quote (entities/keywords/queries)
      - Runs web search + SBERT span matching via SearchService
      - Returns DetectedQuote-shaped data that the UI already consumes.
    """
    try:
        if not request.quotes:
            return AnalyzeQuotesResponse(quotes=[])

        article_text = _build_article_text(request.article)
        if not article_text:
            return AnalyzeQuotesResponse(quotes=[])

        analyzed_quotes: List[AnalyzedQuote] = []

        for quote in request.quotes:
            quote_text = (quote.text or "").strip()
            if not quote_text:
                continue

            # Step 1: pipeline for this quote
            pipeline_result = QuoteService.process_article(
                text=article_text,
                quote=quote_text,
                date=request.article.date,
                top_n=15,
                top_k=3,
                rollcall=False,
                device=0,
                debug=API_DEBUG,
            )

            is_trump_context = _check_trump_context(pipeline_result, article_text, quote_text)

            # Rollcall 모드일 경우, 동일한 extraction 결과를 사용해 쿼리만 재구성
            if is_trump_context:
                try:
                    rollcall_queries = generate_search_query(
                        entities_by_type=pipeline_result.get("entities_by_type", {}) or {},
                        keywords=pipeline_result.get("keywords", []) or [],
                        top_k=3,
                        quote_sentence=quote_text,
                        article_date=request.article.date,
                        rollcall_mode=True,
                        entities=pipeline_result.get("entities"),
                    )
                    pipeline_result["queries"] = rollcall_queries
                except Exception as e:
                    logger.warning("Rollcall query generation failed, falling back to default: %s", e)

            queries = pipeline_result.get("queries") or {}
            query_en = queries.get("en")
            query_ko = queries.get("ko")
            query = query_en or query_ko

            if not query:
                analyzed_quotes.append(
                    AnalyzedQuote(
                        id=quote.id,
                        text=quote_text,
                        speaker=quote.speaker or "Article quote",
                        sources=[],
                    )
                )
                continue

            # Step 2: web search (Trump 컨텍스트 + rollcall=True → Rollcall 우선)
            search_items = SearchService.search(
                query=query,
                is_trump_context=is_trump_context,
                rollcall=is_trump_context,
                num_results=5,
                debug=API_DEBUG,
            )

            if not search_items:
                analyzed_quotes.append(
                    AnalyzedQuote(
                        id=quote.id,
                        text=quote_text,
                        speaker=quote.speaker or "Article quote",
                        sources=[],
                    )
                )
                continue

            # Step 3: SBERT-based span matching
            best_span = SearchService.find_best_match(
                quote_text=quote_text,
                search_items=search_items,
                query_en=query_en,
                min_score=0.0,
                num_before=1,
                num_after=1,
            )

            if not best_span:
                analyzed_quotes.append(
                    AnalyzedQuote(
                        id=quote.id,
                        text=quote_text,
                        speaker=quote.speaker or "Article quote",
                        sources=[],
                    )
                )
                continue

            candidates = best_span.get("top_k_candidates") or [best_span]
            sources: List[QuoteSource] = []

            for idx, cand in enumerate(candidates, start=1):
                url = cand.get("url")
                span_text = cand.get("span_text") or cand.get("best_sentence") or ""
                if not url or not span_text:
                    continue

                raw_score = cand.get("best_score", 0.0)
                sim = _normalize_similarity(raw_score)
                dist = _estimate_distortion(sim)

                sim_100 = max(0, min(100, int(round(sim * 100))))
                dist_100 = max(0, min(100, int(round(dist * 100))))

                raw_id = f"{url}|{span_text}"
                candidate_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:16]

                # Lightweight title derived from domain
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(url)
                    domain = parsed.netloc or url
                except Exception:
                    domain = url
                title = f"{domain} candidate #{idx}"

                scores = QuoteSourceScores(
                    semanticReduction=dist_100,
                    interpretiveExtension=dist_100,
                    lexicalColoring=dist_100,
                )

                sources.append(
                    QuoteSource(
                        id=idx,
                        title=title,
                        sourceLink=url,
                        originalText=span_text,
                        distortionScore=dist_100,
                        similarityScore=sim_100,
                        scores=scores,
                        candidate_id=candidate_id,
                    )
                )

            analyzed_quotes.append(
                AnalyzedQuote(
                    id=quote.id,
                    text=quote_text,
                    speaker=quote.speaker or "Article quote",
                    sources=sources,
                )
            )

        return AnalyzeQuotesResponse(quotes=analyzed_quotes)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in /api/v1/analyze-quotes: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _check_trump_context(pipeline_result: dict, text: str, quote: Optional[str]) -> bool:
    """
    Check if the context is Trump-related.

    NER + 원문 텍스트/인용문 모두를 보되,
    조건을 조금 더 관대하게 해서 "트럼프"/"trump"만 나와도 Trump 컨텍스트로 본다.
    """
    TRUMP_NAME_VARIANTS = [
        "트럼프",
        "도널드 트럼프",
        "도널드 J 트럼프",
        "donald trump",
        "donald j. trump",
        "president trump",
    ]

    # 1) NER 엔티티(PER/PERSON)에 트럼프 변형이 있는지 체크
    entities_by_type = pipeline_result.get("entities_by_type", {}) or {}
    persons: list[str] = []
    for key in ("PER", "PERSON"):
        persons.extend(entities_by_type.get(key, []) or [])

    norm_persons = [str(p).lower() for p in persons]
    for p in norm_persons:
        for variant in TRUMP_NAME_VARIANTS:
            if variant.lower() in p:
                return True

    # 2) 텍스트/인용문 직접 검사 (좀 더 관대하게)
    text_lower = text.lower()
    quote_text = quote or ""
    quote_lower = quote_text.lower()

    if (
        "트럼프" in quote_text
        or "도널드 트럼프" in quote_text
        or "trump" in quote_lower
        or "트럼프" in text
        or "donald trump" in text_lower
        or "president trump" in text_lower
    ):
        return True

    return False


if __name__ == "__main__":
    import uvicorn
    from quote_backend.config import API_HOST, API_PORT
    
    uvicorn.run(
        "quote_backend.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_DEBUG,
    )

