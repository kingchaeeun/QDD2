"""
Person-name resolution helpers (Wikidata first, translation fallback).
"""

from typing import Dict, Optional

import requests

from qdd2 import config
from qdd2.name_lexicon import PERSON_NAME_LEXICON
from qdd2.translation import translate_ko_to_en

def resolve_person_name_en(name_ko: str) -> str:
    """
    한국어 인명 → 검색용 영어 이름
    1) 로컬 인명사전 우선
    2) 없으면 기존(위키데이터/번역) 로직
    """
    name_ko = (name_ko or "").strip()

    # 1) 정확 매칭
    if name_ko in PERSON_NAME_LEXICON:
        return PERSON_NAME_LEXICON[name_ko]

    # 2) 부분 포함 매칭(예: "이스라엘의 네타냐후 총리" 같은 경우)
    for key, val in PERSON_NAME_LEXICON.items():
        if key in name_ko:
            return val

    # 3) fallback: 기존 Wikidata/번역 로직
    #    (이미 갖고 있는 코드 그대로 호출)
    # ex) wikidata_hit = query_wikidata(name_ko)
    # ...
    try:
        return translate_ko_to_en(name_ko)
    except Exception:
        return name_ko

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
    Resolve a Korean person name to English:
    1) Wikidata English label (if any)
    2) Machine translation fallback
    3) If both fail, return the original name.
    """
    info = get_wikidata_english_name(name_ko)
    if isinstance(info, dict) and info.get("en"):
        return info["en"]

    try:
        return translate_ko_to_en(name_ko)
    except Exception:
        return name_ko
