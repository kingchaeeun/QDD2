"""
Person-name resolution helpers (Wikidata first, translation fallback).
"""

from typing import Dict, Optional

import requests

from app import config
from app.name_lexicon import PERSON_NAME_LEXICON
from app.translation import translate_ko_to_en

def get_wikidata_english_name(korean_name: str, timeout: int = 10) -> Dict[str, Optional[str]]:
    """
    Look up a Korean name on Wikidata and return English label if found.
    Returns {"ko": "...", "en": "...", "qid": "..."} or {"error": "..."}.
    """
    search_url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": korean_name,
        "language": "ko",
        "format": "json",
    }
    headers = {"User-Agent": config.HTTP_HEADERS["User-Agent"]}

    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=timeout)
        data = resp.json()
    except Exception:
        return {"error": "Failed to fetch search results"}

    if "search" not in data or not data["search"]:
        return {"error": "No matching Wikidata entry"}

    qid = data["search"][0]["id"]
    detail_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

    try:
        detail = requests.get(detail_url, headers=headers, timeout=timeout).json()
        labels = detail["entities"][qid]["labels"]
    except Exception:
        return {"error": "Failed to fetch entity details"}

    if "en" in labels:
        return {"ko": korean_name, "en": labels["en"]["value"], "qid": qid}
    if "ko" in labels:
        return {"ko": korean_name, "en": None, "qid": qid}
    return {"error": "No labels found"}


def resolve_person_name_en(name_ko: str) -> str:
    """
    한국어 인명 → 검색용 영어 이름
    1) 로컬 인명사전 우선
    2) 없으면 Wikidata/번역 기반 fallback
    """
    name_ko = (name_ko or "").strip()

    # 1) 정확 매칭
    if name_ko in PERSON_NAME_LEXICON:
        return PERSON_NAME_LEXICON[name_ko]

    # 2) 부분 포함 매칭(예: "이스라엘의 네타냐후 총리" 같은 경우)
    for key, val in PERSON_NAME_LEXICON.items():
        if key in name_ko:
            return val

    # 3) fallback: Wikidata → 번역 → 원문
    info = get_wikidata_english_name(name_ko)
    if isinstance(info, dict) and info.get("en"):
        return str(info["en"])

    try:
        return translate_ko_to_en(name_ko)
    except Exception:
        return name_ko
