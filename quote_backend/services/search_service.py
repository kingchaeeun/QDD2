"""
Service for web search and snippet matching.
"""

import logging
from typing import Dict, List, Optional

# Import search functions - will use compatibility wrapper
try:
    from app.search_client import (
        collect_candidates_google_cse,
        google_cse_search,
    )
    from app.rollcall_search import get_search_results
    from app.snippet_matcher import find_best_span_from_candidates_debug
except ImportError:
    # Fallback if modules not yet migrated
    def google_cse_search(*args, **kwargs):
        return {"items": []}

    def collect_candidates_google_cse(*args, **kwargs):  # type: ignore[no-redef]
        return []

    def get_search_results(*args, **kwargs):
        return []

    def find_best_span_from_candidates_debug(*args, **kwargs):
        return None

from quote_backend.utils.translation import translate_ko_to_en

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for web search and source matching.
    """

    @staticmethod
    def search(
        query: str,
        is_trump_context: bool = False,
        rollcall: bool = False,
        num_results: int = 5,
        debug: bool = False,
    ) -> List[Dict]:
        """
        Search for sources using Google CSE or Rollcall.
        
        Args:
            query: Search query
            is_trump_context: Whether this is a Trump-related context
            rollcall: Use rollcall search if Trump context
            num_results: Number of results to return
            debug: Enable debug output
            
        Returns:
            List of search result items
        """
        search_items: List[Dict] = []

        # Trump context + rollcall=True → Rollcall 우선, 실패 시 도메인 제한 CSE
        # 혹시라도 상위 레이어에서 is_trump_context 플래그가 빠져도,
        # 쿼리 문자열에 trump/트럼프가 있으면 Rollcall을 우선 시도한다.
        query_lower = (query or "").lower()
        has_trump_hint = "trump" in query_lower or "트럼프" in query

        if (is_trump_context and rollcall) or has_trump_hint:
            logger.info("[Search] Trump / Rollcall hint detected → using Rollcall search first")
            try:
                rollcall_links = get_search_results(query, top_k=num_results)
            except Exception as e:
                logger.warning("Rollcall search failed, fallback to CSE: %s", e)
                rollcall_links = []

            search_items = [
                {"link": url, "snippet": ""}
                for url in rollcall_links
                if url
            ]

            if not search_items:
                logger.info("[Search] No rollcall results, fallback to domain-prioritized Google CSE")
                try:
                    candidates = collect_candidates_google_cse(
                        query=query,
                        top_per_domain=max(1, num_results // 2),
                        debug=debug,
                    )
                    search_items = [
                        {"link": c.get("url"), "snippet": c.get("snippet", "") or ""}
                        for c in candidates
                        if c.get("url")
                    ]
                except AssertionError as e:
                    logger.warning("Google CSE not configured, skipping external search: %s", e)
                    search_items = []

        # 그 외에는 도메인 우선순위가 반영된 CSE 사용
        else:
            logger.info("[Search] Using Google CSE with whitelisted domains")
            try:
                candidates = collect_candidates_google_cse(
                    query=query,
                    top_per_domain=max(1, num_results // 2),
                    debug=debug,
                )
                search_items = [
                    {"link": c.get("url"), "snippet": c.get("snippet", "") or ""}
                    for c in candidates
                    if c.get("url")
                ]
            except AssertionError as e:
                logger.warning("Google CSE not configured, skipping external search: %s", e)
                search_items = []

        return search_items

    @staticmethod
    def find_best_match(
        quote_text: str,
        search_items: List[Dict],
        query_en: Optional[str] = None,
        min_score: float = 0.2,
        num_before: int = 1,
        num_after: int = 1,
    ) -> Optional[Dict]:
        """
        Find best matching span from search results using SBERT similarity.
        
        Args:
            quote_text: Original quote text (Korean)
            search_items: List of search result items
            query_en: Optional English query as fallback
            min_score: Minimum similarity score threshold
            num_before: Number of sentences before match
            num_after: Number of sentences after match
            
        Returns:
            Best matching span dict or None
        """
        if not search_items:
            return None

        # Translate quote to English
        quote_for_match_en: Optional[str] = None
        if quote_text:
            try:
                quote_for_match_en = translate_ko_to_en(quote_text)
            except Exception as e:
                logger.warning("Quote translation failed, fallback to EN query: %s", e)

        if not quote_for_match_en:
            # fallback: EN 쿼리 자체를 사용
            quote_for_match_en = query_en

        if not quote_for_match_en:
            logger.warning("No English text available for similarity matching.")
            return None

        # Prepare candidates
        candidates = []
        for it in search_items:
            url = it.get("link")
            if not url:
                continue
            snippet = it.get("snippet", "") or ""
            candidates.append(
                {
                    "url": url,
                    "snippet": snippet,
                }
            )

        if not candidates:
            return None

        try:
            best_span = find_best_span_from_candidates_debug(
                quote_en=quote_for_match_en,
                candidates=candidates,
                num_before=num_before,
                num_after=num_after,
                min_score=min_score,
            )
            if best_span:
                logger.info(
                    "[Best Match] Found: score=%.4f, url=%s",
                    best_span.get("best_score", -1.0),
                    best_span.get("url", ""),
                )
            return best_span
        except Exception as e:
            logger.warning("SBERT snippet matching failed: %s", e)
            return None

