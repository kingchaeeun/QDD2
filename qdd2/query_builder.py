"""
Search-query construction utilities.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from qdd2.name_resolution import resolve_person_name_en
from qdd2.translation import translate_ko_to_en

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
    if rollcall_mode and article_date:
        """
        [Rollcall 모드 - NER 중심]
        구조: Speaker + Date + (포커스 엔티티 1개: NER 기반)
        """
        # 1) 날짜 영어 포맷 변환
        try:
            dt = datetime.strptime(article_date, "%Y-%m-%d")
            date_en = dt.strftime("%B %d %Y")  # 예: November 26 2025
        except Exception:
            date_en = article_date

        target_word_ko = ""
        target_word_en = ""

        # 2-1) 1순위: 원본 NER 엔티티에서 포커스 엔티티 선택
        focus_ko, focus_en = _select_rollcall_focus_entity(
            entities=entities,
            speaker_ko=speaker_ko,
        )
        if focus_ko:
            target_word_ko = focus_ko
            target_word_en = focus_en

        # 2-2) 2순위: entities_by_type["LOC"] (loc_list) 사용
        if (not target_word_ko) and loc_list:
            target_word_ko = loc_list[0]
            if locs_en_tokens:
                target_word_en = locs_en_tokens[0]
            else:
                target_word_en = target_word_ko

        # 2-3) 3순위: 그래도 없으면 KeyBERT keywords에서 1개만 fallback
        if (not target_word_ko) and keywords:
            # 화자 이름이 들어간 키워드는 전부 제외하고,
            # 키워드 문구 안에서 '명사 같아 보이는 토큰' 하나만 뽑아서 사용
            for kw_text, _ in keywords:
                if not kw_text:
                    continue

                # 키워드 전체에 화자 이름이 들어가면 스킵
                if speaker_ko and (speaker_ko in kw_text):
                    continue

                chosen_base = ""
                # 키워드 문구를 토큰 단위로 쪼개서 검사
                for raw_tok in kw_text.split():
                    tok = raw_tok.strip()
                    if speaker_ko and (speaker_ko in tok):
                        # 토큰에 화자 이름 들어가면 스킵
                        continue
                    if len(tok) < 2:
                        continue
                    # 숫자 섞인 건 버림
                    if re.search(r"\d", tok):
                        continue
                    # 완성형 한글만 우선 사용 (필요에 따라 완화 가능)
                    if not re.fullmatch(r"[가-힣]+", tok):
                        continue

                    # 조사/어미를 떼서 명사 근간만 남기고 길이 체크
                    base = re.sub(
                        r"(에서|에게|부터|까지|으로써|으로서|으로|만큼|뿐|조차|마저|마다|처럼|같이|보다|께서|라고|하고|와|과|랑|이랑|은|는|이|가|을|를|의)$",
                        "",
                        tok,
                    )
                    if len(base) < 2:
                        continue

                    chosen_base = base
                    break  # 이 키워드에서 쓸 토큰 하나 찾았으면 탈출

                if chosen_base:
                    target_word_ko = chosen_base
                    try:
                        kw_en_full = translate_ko_to_en(chosen_base)
                        target_word_en = " ".join(kw_en_full.split()[:3])
                    except Exception:
                        target_word_en = chosen_base
                    break  # fallback 완성했으니 전체 루프 탈출

        # 3) EN 쿼리 조립: [Speaker] [Date] [Entity?]
        parts_en: List[str] = []
        if speaker_en:
            parts_en.append(speaker_en)
        if date_en:
            parts_en.append(date_en)
        if target_word_en:
            parts_en.append(target_word_en)
        query_en = " ".join(parts_en).strip() or None

        # 4) KO 쿼리 조립: [Speaker] [Date] [Entity?]
        parts_ko: List[str] = []
        if speaker_ko:
            parts_ko.append(speaker_ko)
        if article_date:
            parts_ko.append(article_date)
        if target_word_ko:
            parts_ko.append(target_word_ko)
        query_ko = " ".join(parts_ko).strip() or None

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
