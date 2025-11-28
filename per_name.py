import requests

def get_wikidata_english_name(korean_name: str) -> dict:
    """
    Wikidata에서 한국어 이름으로 엔티티 검색 후 영어 라벨 가져오기
    반환 예시:
      {"ko": "시진핑", "en": "Xi Jinping", "qid": "Q82990"}
    실패 시:
      {"error": "..."}
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": korean_name,
        "language": "ko",
        "format": "json",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Research; NLP Project)",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
    except Exception:
        return {"error": "JSON 응답 실패"}

    if "search" not in data or not data["search"]:
        return {"error": "해당 이름으로 Wikidata 검색 실패"}

    qid = data["search"][0]["id"]  # 첫 번째 후보 선택

    # 두 번째 요청: 상세 정보에서 라벨 추출
    url_detail = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    try:
        detail = requests.get(url_detail, headers=headers, timeout=10).json()
        labels = detail["entities"][qid]["labels"]
    except Exception:
        return {"error": "파싱 실패"}

    if "en" in labels:
        return {"ko": korean_name, "en": labels["en"]["value"], "qid": qid}
    elif "ko" in labels:
        return {"ko": korean_name, "en": None, "qid": qid}
    else:
        return {"error": "라벨 정보 부족"}