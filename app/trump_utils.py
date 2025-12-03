# qdd2/trump_utils.py

from __future__ import annotations
from typing import Dict, Any, List

TRUMP_NAME_VARIANTS: List[str] = [
    "트럼프",
    "도널드 트럼프",
    "도널드 J 트럼프",
    "donald trump",
    "donald j. trump",
    "president trump",
]


def _normalize(s: str) -> str:
    return str(s).lower()


def contains_trump_entity(pipeline_result: Dict[str, Any]) -> bool:
    """
    build_queries_from_text 결과의 NER 엔티티 중
    트럼프(도널드 트럼프)가 하나라도 포함돼 있으면 True.
    PER/PERSON 두 라벨을 모두 확인한다.
    """
    entities_by_type = pipeline_result.get("entities_by_type", {}) or {}

    persons: List[str] = []
    for key in ("PER", "PERSON"):
        persons.extend(entities_by_type.get(key, []) or [])

    norm_persons = [_normalize(p) for p in persons]

    for p in norm_persons:
        for variant in TRUMP_NAME_VARIANTS:
            if variant.lower() in p:
                return True
    return False


def is_trump_like_text(text: str | None) -> bool:
    """
    단순 문자열 기반 트럼프 감지:
    - '트럼프', '도널드 트럼프'
    - 'donald trump', 'president trump'
    """
    if not text:
        return False
    t = _normalize(text)

    if "트럼프" in text or "도널드 트럼프" in text:
        return True
    if "donald trump" in t or "president trump" in t or "trump" in t:
        return True
    return False


def contains_whitehouse_cue(text: str | None) -> bool:
    """
    백악관/white house 관련 단서가 있는지 여부.
    """
    if not text:
        return False
    t = _normalize(text)
    return ("백악관" in text) or ("white house" in t)


def detect_trump_context(
    article_text: str,
    quote_text: str | None,
    pipeline_result: Dict[str, Any],
) -> bool:
    """
    NER + 문자열 단서를 모두 고려해서
    '트럼프/백악관' 컨텍스트인지 최종 판단.
    """
    # 1) NER 기반
    is_trump = contains_trump_entity(pipeline_result)

    # 2) 기사/인용문 문자열 기반
    if not is_trump:
        if is_trump_like_text(article_text):
            is_trump = True
        elif is_trump_like_text(quote_text):
            is_trump = True

    # 3) 백악관 단서
    if contains_whitehouse_cue(article_text) or contains_whitehouse_cue(quote_text):
        is_trump = True

    return is_trump
