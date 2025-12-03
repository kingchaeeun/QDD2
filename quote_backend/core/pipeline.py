"""
High-level helpers that compose extraction + query building.
"""

import logging
import re
from typing import Dict, Optional

from quote_backend.core.keywords import extract_keywords_with_ner
from quote_backend.core.query_builder import generate_search_query

logger = logging.getLogger(__name__)


def _infer_article_date_from_entities(entities_by_type: Dict[str, list]) -> Optional[str]:
    """
    Try to infer article_date (YYYY-MM-DD) from NER date entities (DAT).

    지원 형태 (최소 휴리스틱):
      - 2024-11-29 / 2024.11.29 / 2024/11/29
      - 2024년 11월 29일
      - 20241129
    """
    dat_entities = entities_by_type.get("DAT") or []
    if not dat_entities:
        return None

    for raw in dat_entities:
        s = str(raw).strip()
        if not s:
            continue

        # 1) 2024-11-29 / 2024.11.29 / 2024/11/29
        m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", s)
        if m:
            y, mth, d = m.groups()
            return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"

        # 2) 2024년 11월 29일
        m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?", s)
        if m:
            y, mth, d = m.groups()
            return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"

        # 3) 20241129
        m = re.search(r"\b(\d{4})(\d{2})(\d{2})\b", s)
        if m:
            y, mth, d = m.groups()
            return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"

    return None


def build_queries_from_text(
    text: str,
    top_n_keywords: int = 15,
    top_k_for_query: int = 3,
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,
    rollcall_mode: bool = False,
    device: int = 0,
    debug: bool = False,
) -> Dict:
    """
    Convenience wrapper:
      1) extract keywords + entities
      2) (optionally) infer article_date from NER (DAT)
      3) build ko/en queries
    """
    extraction = extract_keywords_with_ner(
        text,
        top_n=top_n_keywords,
        device=device,
        debug=debug,
    )
    logger.info(
        "Extraction complete: %d entities, %d keywords",
        len(extraction["entities"]),
        len(extraction["keywords"]),
    )
    logger.debug("Entities by type: %s", extraction["entities_by_type"])
    logger.debug("Top keywords (scored): %s", extraction["keywords"])

    entities_by_type = extraction.get("entities_by_type", {}) or {}

    # Caller가 date를 안 줬으면, DAT NER에서 날짜를 추론해본다.
    effective_article_date = article_date
    if not effective_article_date:
        inferred = _infer_article_date_from_entities(entities_by_type)
        if inferred:
            logger.info("Inferred article_date from NER (DAT): %s", inferred)
            effective_article_date = inferred

    queries = generate_search_query(
        entities_by_type,
        extraction["keywords"],
        top_k=top_k_for_query,
        quote_sentence=quote_sentence,
        article_date=effective_article_date,
        rollcall_mode=rollcall_mode,
    )
    logger.info("Query generation complete (ko/en)")
    logger.debug("KO query: %s", queries["ko"])
    logger.debug("EN query: %s", queries["en"])

    return {
        **extraction,
        "queries": queries,
    }

