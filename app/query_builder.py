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

def _select_rollcall_focus_entity(
    entities: Optional[List[Dict[str, str]]],
    speaker_ko: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Rollcall 모드에서 사용할 '포커스 엔티티' 1개 선택.

    - 스피커와 겹치는 PS는 제외
    - 우선순위: LC > OG > PS
    - 같은 text는 빈도/길이 기반으로 스코어링
    - 반환: (ko_text, en_text) (없으면 ("",""))
    """
    if not entities:
        return "", ""

    # monologg/koelectra-base-v3-naver-ner 기준
    LABEL_PRIORITY = {
        "LC": 3,  # 장소
        "OG": 2,  # 조직
        "PS": 1,  # 사람(스피커 제외)
    }

    stats: Dict[str, Dict[str, object]] = {}

    for ent in entities:
        text_val = (ent.get("text") or "").strip()
        if not text_val:
            continue

        raw_label = (
            ent.get("label")
            or ent.get("tag")
            or ent.get("ner")
            or ""
        )
        label = raw_label.replace("B-", "").replace("I-", "")

        # 관심 없는 레이블은 제외
        if label not in LABEL_PRIORITY:
            continue

        # 스피커 이름과 겹치는 PS는 제외
        if label == "PS" and speaker_ko:
            if text_val in speaker_ko or speaker_ko in text_val:
                continue

        key = text_val  # 같은 text는 하나로 묶음
        entry = stats.get(key)
        if entry is None:
            stats[key] = {
                "label": label,
                "count": 1,
                "len": len(text_val),
                "translated": ent.get("translated", text_val),
            }
        else:
            entry["count"] = int(entry["count"]) + 1
            entry["len"] = max(int(entry["len"]), len(text_val))

    if not stats:
        return "", ""

    # 스코어: 레이블 우선순위 -> 등장 빈도 -> 길이
    def _score_item(item):
        text, info = item
        label = info["label"]
        count = info["count"]
        length = info["len"]
        base = LABEL_PRIORITY.get(label, 0)
        return (base, count, length)

    best_text, best_info = sorted(
        stats.items(),
        key=_score_item,
        reverse=True,
    )[0]

    return best_text, str(best_info.get("translated", best_text))


def generate_search_query(
    entities_by_type: Dict[str, List[str]],
    keywords: List[Tuple[str, float]],
    top_k: int = 3,
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,  # YYYY-MM-DD
    rollcall_mode: bool = False,
    use_wikidata: bool = True,
    # 🔥 추가: NER 엔티티 원본 리스트 (text/label/translated 등 들어있는 dict 리스트)
    entities: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Optional[str]]:
    """
    Build Korean/English search queries using entities + keywords.

    rollcall_mode=True:
        query_ko/en = [speaker] [article_date] [NER 고유명사 1개 (PS/OG/LC)]
    default:
        query = speaker + location tokens + keyword tokens + optional quoted sentence
    """
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

        # 날짜 변환 동일
        article_date_str = str(article_date).strip()
        date_en = None
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", article_date_str):
                dt = datetime.strptime(article_date_str, "%Y-%m-%d")
                date_en = dt.strftime("%B %d %Y")
            else:
                date_en = article_date_str
        except:
            date_en = article_date_str

        # =======================================
        # 2) PER 태그 중 발화자 제외 1명 선택
        # =======================================
        target_per_ko = ""
        target_per_en = ""

        per_list = entities_by_type.get("PER", [])
        for per in per_list:
            if speaker_ko and (per == speaker_ko):
                continue
            target_per_ko = per
            # 영어 변환
            try:
                target_per_en = translate_ko_to_en(per)
                target_per_en = " ".join(target_per_en.split()[:3])
            except:
                target_per_en = per
            break

        # =======================================
        # 3) 고유명사 키워드 1개 선택 (LOC/ORG > KeyBERT)
        # =======================================
        extra_kw_ko = ""
        extra_kw_en = ""

        # 3-1) LOC 또는 ORG 우선 사용
        loc_list = entities_by_type.get("LOC", [])
        org_list = entities_by_type.get("ORG", [])

        chosen_list = loc_list if loc_list else org_list

        if chosen_list:
            extra_kw_ko = chosen_list[0]
            try:
                extra_en_full = translate_ko_to_en(extra_kw_ko)
                extra_kw_en = " ".join(extra_en_full.split()[:3])
            except:
                extra_kw_en = extra_kw_ko
        else:
            # 3-2) LOC/ORG 없으면 KeyBERT에서 명사 하나
            if keywords:
                for kw_text, _ in keywords:
                    if not kw_text:
                        continue
                    if speaker_ko and (speaker_ko in kw_text):
                        continue
                    if len(kw_text) < 2:
                        continue

                    extra_kw_ko = kw_text.strip()
                    try:
                        extra_kw_en = " ".join(translate_ko_to_en(extra_kw_ko).split()[:3])
                    except:
                        extra_kw_en = extra_kw_ko
                    break

        # ===========================
        # 최종 쿼리 구성 (EN / KO)
        # ===========================
        parts_en = []
        if speaker_en:
            parts_en.append(str(speaker_en))
        if date_en:
            parts_en.append(str(date_en))
        if target_per_en:
            parts_en.append(str(target_per_en))
        if extra_kw_en:
            parts_en.append(str(extra_kw_en))
        query_en = " ".join(parts_en).strip() or None

        parts_ko = []
        if speaker_ko:
            parts_ko.append(str(speaker_ko))
        if article_date_str:
            parts_ko.append(article_date_str)
        if target_per_ko:
            parts_ko.append(str(target_per_ko))
        if extra_kw_ko:
            parts_ko.append(str(extra_kw_ko))
        query_ko = " ".join(parts_ko).strip() or None

        logger.info("[RollcallQuery] ko=%s", query_ko)
        logger.info("[RollcallQuery] en=%s", query_en)

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
