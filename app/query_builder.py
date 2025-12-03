"""
Search-query construction utilities.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.name_resolution import resolve_person_name_en
from app.translation import translate_ko_to_en

logger = logging.getLogger(__name__)

def _format_date_en(article_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    article_date를 문자열로 받아서
    - 원본 문자열 (article_date_str)
    - 영어 포맷(예: November 30, 2025) 을 튜플로 반환

    인식 가능한 포맷: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    """
    if article_date is None:
        return None, None

    s = str(article_date).strip()
    if not s:
        return None, None

    dt = None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        # 못 파싱하면 그냥 원본을 그대로 쓰도록
        return s, s

    # 원하는 포맷: November 30, 2025  (쉼표 포함)
    date_en = dt.strftime("%B %d %Y")
    return s, date_en


def _normalize_token(tok: str) -> str:
    """Normalize token for deduplication: lowercase, strip punctuation/extra spaces."""
    normalized = re.sub(r"[^\w\s]", " ", tok).lower()
    return " ".join(normalized.split()).strip()


def _dedupe_preserve(seq: List[str]) -> List[str]:
    """Remove duplicates while preserving order and ignoring empty tokens (punct/space-insensitive)."""
    seen = set()
    out: List[str] = []
    for item in seq:
        if not item:
            continue
        norm = _normalize_token(item)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(item)
    return out


def generate_search_query(
    entities_by_type: Dict[str, List[str]],
    keywords: List[Tuple[str, float]],
    top_k: int = 3,
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,  # YYYY-MM-DD
    rollcall_mode: bool = False,
    use_wikidata: bool = True
) -> Dict[str, Optional[str]]:
    """
    Build Korean/English search queries using entities + keywords.

    rollcall_mode=True:
        query_ko/en = [speaker] [article_date] [NER 고유명사 1개 (PS/OG/LC)]
    default:
        query = speaker + location tokens + keyword tokens + optional quoted sentence
    """
    article_date_str, date_en = _format_date_en(article_date)
    per_list = entities_by_type.get("PER", [])
    if not per_list:
        return {"ko": None, "en": None}

    speaker_ko = per_list[0]
    if use_wikidata:
        speaker_en = resolve_person_name_en(speaker_ko)
    else:
        try:
            speaker_en = translate_ko_to_en(speaker_ko)
        except Exception:
            speaker_en = speaker_ko

    # LOC는 일반 모드에서만 사용할 거라 그대로 둠
    loc_list = entities_by_type.get("LOC", [])[:2]
    loc_list = _dedupe_preserve(loc_list)
    locs_ko = " ".join(loc_list)
    locs_en_tokens: List[str] = []
    for loc in loc_list:
        try:
            loc_en_full = translate_ko_to_en(loc)
            loc_en_first = loc_en_full.split(",")[0]
            loc_en_first = " ".join(loc_en_first.split()[:2])
            if loc_en_first:
                locs_en_tokens.append(loc_en_first)
        except Exception:
            logger.warning("Location translation failed, falling back to original: %s", loc)
            locs_en_tokens.append(loc)

    top_kws_ko = [kw for kw, _ in keywords[:top_k]]
    top_kws_ko = _dedupe_preserve(top_kws_ko)
    kws_en_tokens: List[str] = []
    for kw_ko in top_kws_ko:
        try:
            kw_en_full = translate_ko_to_en(kw_ko)
            kw_en_trim = " ".join(kw_en_full.split()[:3])
            if kw_en_trim:
                kws_en_tokens.append(kw_en_trim)
        except Exception:
            logger.warning("Keyword translation failed, falling back to original: %s", kw_ko)
            kws_en_tokens.append(kw_ko)

    quote_en_full: Optional[str] = None
    if quote_sentence:
        try:
            quote_en_full = translate_ko_to_en(quote_sentence)
        except Exception:
            quote_en_full = None

    # =========================
    # 1) Rollcall 모드 전용 블록
    # =========================
    if rollcall_mode and article_date is not None:

        # article_date_str, date_en 는 함수 시작부에서 _format_date_en 로 이미 계산됨
        # article_date_str: 원본 (예: "2025.11.30")
        # date_en        : "November 30, 2025"

        # --- (선택) speaker_en 정제 함수 ---
        def normalize_name_en(name: str, max_words: int = 3) -> str:
            import re as _re
            name = _re.sub(r"[^A-Za-z\s]", " ", str(name))
            name = _re.sub(r"\s+", " ", name).strip()
            parts = name.split()
            if not parts:
                return ""
            return " ".join(parts[:max_words])

        # ===========================
        # 최종 쿼리 구성 (EN / KO)
        # ===========================
        # EN: 발화자 + 날짜
        parts_en = []
        if speaker_en:
            speaker_en_clean = normalize_name_en(speaker_en, max_words=3)
            if speaker_en_clean:
                parts_en.append(speaker_en_clean)
        if date_en:
            parts_en.append(date_en)  # ← 여기
        query_en = " ".join(parts_en).strip() or None

        # KO: 발화자 + 날짜
        parts_ko = []
        if speaker_ko:
            parts_ko.append(str(speaker_ko))
        if article_date_str:
            parts_ko.append(article_date_str)
        query_ko = " ".join(parts_ko).strip() or None

        logger.info("[RollcallQuery] ko=%s", query_ko)
        logger.info("[RollcallQuery] en=%s", query_en)

        # 롤콜 모드에서는 여기서 바로 종료
        return {"ko": query_ko, "en": query_en}

    # =========================
    # 2) 일반 모드 (기존 로직)
    # =========================
    query_en_tokens: List[str] = _dedupe_preserve(
        [speaker_en] + locs_en_tokens + kws_en_tokens
    )
    if quote_en_full:
        query_en_tokens.append(quote_en_full)
    query_en = " ".join(query_en_tokens).strip()

    query_ko_parts = [speaker_ko]
    if locs_ko:
        query_ko_parts.append(locs_ko)
    if top_kws_ko:
        query_ko_parts.append(" ".join(top_kws_ko))
    if quote_sentence:
        query_ko_parts.append(quote_sentence)
    query_ko = " ".join(
        _dedupe_preserve(" ".join(query_ko_parts).split())
    ).strip()

    return {"ko": query_ko or None, "en": query_en or None}
