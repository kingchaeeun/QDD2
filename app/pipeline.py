"""
High-level helpers that compose extraction + query building.
"""

import logging
from typing import Dict, Optional

from qdd2.keywords import extract_keywords_with_ner
from qdd2.query_builder import generate_search_query

logger = logging.getLogger(__name__)


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
      2) build ko/en queries
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
    queries = generate_search_query(
        extraction["entities_by_type"],
        extraction["keywords"],
        top_k=top_k_for_query,
        quote_sentence=quote_sentence,
        article_date=article_date,
        rollcall_mode=rollcall_mode,
    )
    logger.info("Query generation complete (ko/en)")
    logger.debug("KO query: %s", queries["ko"])
    logger.debug("EN query: %s", queries["en"])

    return {
        **extraction,
        "queries": queries,
    }
