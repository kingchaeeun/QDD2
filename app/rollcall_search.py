"""
Rollcall / Factba.se Trump transcript search using the public JSON endpoint.

기존 Selenium 기반 구현을 제거하고, 다음과 같은 JSON API를 사용한다:

    https://rollcall.com/wp-json/factbase/v1/search

대화형 예시:

    from requests import get
    r = get(
        "https://rollcall.com/wp-json/factbase/v1/search"
        "?q=lee+trump&media=&type=&sort=date&location=all&place=all&page=1&format=json"
    )
    r.json()

여기서는 쿼리 생성 로직(문자열 query)은 그대로 두고,
공백을 `+` 로 치환해 q 파라미터에 넣어 요청한 뒤,
JSON 응답에서 날짜가 최신인 transcript 링크들을 반환한다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests


logger = logging.getLogger(__name__)

API_URL = "https://rollcall.com/wp-json/factbase/v1/search"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }
)


def _parse_item_date(item: Dict[str, Any]) -> Optional[datetime]:
    """
    Rollcall/Factsba.se 항목에서 날짜 필드를 찾아 datetime 으로 파싱한다.

    필드 후보:
    - 'date'
    - 'post_date'
    - 'post_date_gmt'
    """
    raw = (
        item.get("date")
        or item.get("post_date")
        or item.get("post_date_gmt")
        or ""
    )
    if not raw:
        return None

    s = str(raw).strip()
    # 보통 'YYYY-MM-DD HH:MM:SS' 또는 'YYYY-MM-DDTHH:MM:SS' 형태
    s = s.replace("T", " ")
    s = s[:19]  # 초 단위까지만 사용

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _extract_item_url(item: Dict[str, Any]) -> Optional[str]:
    """
    JSON 항목에서 transcript 페이지 URL 후보를 추출한다.

    필드 후보:
    - 'permalink'
    - 'link'
    - 'url'
    """
    for key in ("permalink", "link", "url"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def get_search_results(query: str, top_k: int = 5) -> List[str]:
    """
    Rollcall / Factba.se Trump transcript 검색.

    Args:
        query: 기존 파이프라인에서 생성된 영어 쿼리 문자열
        top_k: 상위 몇 개의 transcript 링크를 반환할지

    Returns:
        최신 날짜 순으로 정렬된 transcript URL 리스트 (최대 top_k 개)
    """
    if not query or not isinstance(query, str):
        return []

    params = {
        # 사용자가 제안한 것처럼 공백을 '+' 로 치환해서 그대로 q 에 넣어 보낸다.
        # requests 가 한 번만 URL 인코딩하게 두고, 여기서는 이 이상 인코딩하지 않는다.
        "q": query.replace(" ", "+"),
        "media": "",
        "type": "",
        "sort": "date",  # 최신 순
        "location": "all",
        "place": "all",
        "page": 1,
        "format": "json",
    }

    try:
        resp = SESSION.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Rollcall JSON search request failed: %s", exc)
        return []

    try:
        data = resp.json()
    except ValueError as exc:
        logger.warning("Rollcall JSON search returned non-JSON response: %s", exc)
        return []

    # 응답 형태가 리스트 또는 {'results': [...]} 등일 수 있으므로 유연하게 처리
    results: List[Dict[str, Any]]
    if isinstance(data, list):
        results = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        maybe_list = data.get("results") or data.get("items") or []
        if isinstance(maybe_list, list):
            results = [x for x in maybe_list if isinstance(x, dict)]
        else:
            results = []
    else:
        results = []

    if not results:
        return []

    # 날짜 기준으로 최신 순 정렬
    def sort_key(item: Dict[str, Any]) -> datetime:
        dt = _parse_item_date(item)
        # 날짜가 없으면 가장 오래된 것으로 취급
        return dt or datetime.min

    results_sorted = sorted(results, key=sort_key, reverse=True)

    links: List[str] = []
    for item in results_sorted:
        url = _extract_item_url(item)
        if not url:
            continue
        if "transcript" not in url:
            # 안전하게 transcript 페이지만 사용
            continue
        links.append(url)
        if len(links) >= max(1, int(top_k)):
            break

    return links


# 간단한 CLI 테스트: python app/rollcall_search.py
if __name__ == "__main__":
    test_query = "lee trump"
    links = get_search_results(test_query, top_k=5)

    print("\n=== Top Rollcall JSON Search Results ===")
    for i, link in enumerate(links, start=1):
        print(f"{i}. {link}")
    if not links:
        print("❌ No results found.")