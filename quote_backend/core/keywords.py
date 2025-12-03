"""
Keyword extraction and NER-informed re-ranking.
"""

from typing import Dict, List, Sequence, Tuple

from quote_backend.config import DEFAULT_DEVICE, RELATION_KEYWORDS
from quote_backend.core.entities import extract_ner_entities
from quote_backend.models.loaders import get_keyword_model
from quote_backend.utils.text_utils import normalize_korean_phrase


def rerank_with_ner_boost(
    keywords: Sequence[Tuple[str, float]],
    entities: Sequence[Dict],
    alpha: float = 0.7,
    beta: float = 0.3,
    relation_keywords: Sequence[str] = None,
) -> List[Tuple[str, float]]:
    """
    Boost keyword scores when they include entities or relation-like terms.
    
    Args:
        keywords: Sequence of (phrase, score) tuples
        entities: Sequence of entity dicts with 'word' key
        alpha: Weight for original score
        beta: Weight for bonus score
        relation_keywords: Custom relation keywords (defaults to config)
        
    Returns:
        Rescored and deduplicated keywords sorted by score
    """
    rel_terms = {normalize_korean_phrase(r) for r in (relation_keywords or RELATION_KEYWORDS)}
    ent_terms = {normalize_korean_phrase(e["word"]) for e in entities}

    rescored = []
    for phrase, score in keywords:
        normalized = normalize_korean_phrase(phrase)
        has_entity = any(et and et in normalized for et in ent_terms)
        has_relation = any(rt and rt in normalized for rt in rel_terms)

        bonus = 0.0
        if has_entity and has_relation:
            bonus = 1.0
        elif has_entity or has_relation:
            bonus = 0.6

        rescored.append((phrase, alpha * score + beta * bonus))

    deduped = {}
    for phrase, score in sorted(rescored, key=lambda x: x[1], reverse=True):
        key = normalize_korean_phrase(phrase)
        if key not in deduped:
            deduped[key] = (phrase, score)

    return sorted(deduped.values(), key=lambda x: x[1], reverse=True)


def extract_keywords_with_ner(
    text: str,
    top_n: int = 15,
    use_mmr: bool = True,
    diversity: float = 0.7,
    alpha: float = 0.7,
    beta: float = 0.3,
    device: int = DEFAULT_DEVICE,
    debug: bool = False,
) -> Dict:
    """
    Extract keywords with KeyBERT, then boost scores using NER + relation hints.
    
    Args:
        text: Input text to process
        top_n: Number of top keywords to return
        use_mmr: Use Maximal Marginal Relevance for diversity
        diversity: Diversity parameter for MMR
        alpha: Weight for original score in reranking
        beta: Weight for bonus score in reranking
        device: Device index (0 for CPU, >0 for GPU)
        debug: Enable debug output
        
    Returns:
        Dictionary with:
        {
          "entities": [...],
          "keywords": [(phrase, score), ...],
          "entities_by_type": {"PER": [...], ...},
        }
    """
    entities = extract_ner_entities(text, device=device, debug=debug)

    kw_model = get_keyword_model()
    base_keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 3),
        top_n=top_n * 3,
        use_mmr=use_mmr,
        diversity=diversity if use_mmr else None,
    )

    reranked_keywords = rerank_with_ner_boost(
        base_keywords,
        entities,
        alpha=alpha,
        beta=beta,
    )

    entities_by_type: Dict[str, List[str]] = {}
    seen_normalized = set()
    for ent in entities:
        label = ent["label"]
        word = ent["word"]
        normalized = normalize_korean_phrase(word)

        is_duplicate = False
        for seen in list(seen_normalized):
            if normalized in seen and normalized != seen:
                is_duplicate = True
                break
            if seen in normalized and normalized != seen:
                seen_normalized.discard(seen)
                for lbl in entities_by_type:
                    entities_by_type[lbl] = [
                        w for w in entities_by_type[lbl] if normalize_korean_phrase(w) != seen
                    ]

        if not is_duplicate:
            seen_normalized.add(normalized)
            entities_by_type.setdefault(label, [])
            if word not in entities_by_type[label]:
                entities_by_type[label].append(word)

    return {
        "entities": entities,
        "keywords": reranked_keywords[:top_n],
        "entities_by_type": entities_by_type,
    }

