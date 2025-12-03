"""
FastAPI application for quote detection backend.
"""

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from quote_backend.config import API_DEBUG, LOG_LEVEL
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
                search_items = SearchService.search(
                    query=query,
                    is_trump_context=is_trump_context,
                    rollcall=request.rollcall,
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


def _check_trump_context(pipeline_result: dict, text: str, quote: Optional[str]) -> bool:
    """
    Check if the context is Trump-related.
    
    Args:
        pipeline_result: Pipeline extraction results
        text: Article text
        quote: Optional quote text
        
    Returns:
        True if Trump context detected
    """
    TRUMP_NAME_VARIANTS = [
        "트럼프",
        "도널드 트럼프",
        "도널드 J 트럼프",
        "donald trump",
        "donald j. trump",
        "president trump",
    ]
    
    # Check NER entities
    entities_by_type = pipeline_result.get("entities_by_type", {}) or {}
    persons: list[str] = []
    for key in ("PER", "PERSON"):
        persons.extend(entities_by_type.get(key, []) or [])
    
    norm_persons = [str(p).lower() for p in persons]
    for p in norm_persons:
        for variant in TRUMP_NAME_VARIANTS:
            if variant.lower() in p:
                return True
    
    # Check text/quote directly
    text_lower = text.lower()
    quote_text = quote or ""
    quote_lower = quote_text.lower()
    
    if (
        "트럼프" in quote_text
        or "도널드 트럼프" in quote_text
        or "trump" in quote_lower
        or ("트럼프" in text and "도널드" in text)
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

