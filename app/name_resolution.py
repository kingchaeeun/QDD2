"""
Person-name resolution helpers (Wikidata first, translation fallback).
"""

from typing import Dict, Optional

import requests

from qdd2 import config
from qdd2.translation import translate_ko_to_en


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
