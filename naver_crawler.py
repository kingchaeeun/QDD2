"""
Naver News '세계(104)' 섹션 크롤러 모듈.

- 헤드라인에 직접 인용문(따옴표)이 있는 기사만 필터링
- 국내 경제/부동산 관련 키워드는 제외
- 결과: category, title, date, content, url 컬럼을 가진 DataFrame 반환

사용 예시 (다른 모듈에서):

    from app.naver_crawler import crawl_world_articles

    df_articles = crawl_world_articles(num_articles=50, days_back=60)
"""

import re
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse, parse_qs

# -------------------------------------------------------------------
# 0. 전역 설정
# -------------------------------------------------------------------

BASE_URL = "https://news.naver.com"
WORLD_SID1 = "104"  # 세계 섹션 코드
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def is_world_section_url(url: str) -> bool:
    """
    기사 URL이 실제로 '세계(104) 섹션'인지 sid 파라미터로 확인.
    - n.news.naver.com/mnews/article/.../?sid=104
    - news.naver.com/main/read.naver?...&sid1=104
    둘 다 처리.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # mnews: sid / main: sid1 둘 다 고려
    sid_vals = qs.get("sid") or qs.get("sid1")
    if not sid_vals:
        return False

    return sid_vals[0] == WORLD_SID1  # "104"


# -------------------------------------------------------------------
# 1. 유틸 함수
# -------------------------------------------------------------------

def clean_text(text: Optional[str]) -> str:
    """
    기사 본문 정제:
      - 괄호/대괄호 안 내용 제거
      - 다중 공백 제거
      - 저작권 문구/하단 링크 제거 등
    """
    if not text:
        return ""

    text = re.sub(r"\([^)]+\)", "", text)       # ( ... )
    text = re.sub(r"\[[^\]]+\]", "", text)      # [ ... ]
    text = re.sub(r"\s{2,}", " ", text)         # 다중 공백
    text = re.sub(r"ⓒ.*?무단전재.*", "", text)  # 저작권 문구
    text = re.sub(r"▶.*", "", text)             # 하단 유도 링크 등

    return text.strip()


def extract_date_ymd(raw_date: Optional[str]) -> str:
    """
    다양한 포맷의 날짜 문자열에서 'YYYY.MM.DD'만 추출.
    예:
      - '2024.12.02. 오전 10:31'  -> '2024.12.02'
      - '2024-12-02 10:31:00'     -> '2024.12.02'
    """
    if not raw_date:
        return ""

    m = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", raw_date)
    if m:
        yyyy, mm, dd = m.groups()
        return f"{yyyy}.{mm}.{dd}"
    return raw_date.strip()


def get_html(url: str, max_retry: int = 3, sleep: float = 0.5) -> Optional[str]:
    """
    단순 HTML GET + 재시도 로직.
    """
    for _ in range(max_retry):
        try:
            resp = session.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            time.sleep(sleep)
    return None


def has_direct_quote(text: str, min_chars: int = 3) -> bool:
    """
    직접 인용문(큰따옴표) 존재 여부를 판단.
    - “ ”, 『 』, 「 」 등은 전부 " 로 통일 후 처리
    - 따옴표 안에 한글/영문 문자가 min_chars개 이상 있을 때만 True
    - 여기서는 '제목(헤드라인)'에 쓰는 것을 전제
    """
    if not text:
        return False

    # 다양한 따옴표를 " 로 통일
    normalized = (
        text.replace("“", '"')
            .replace("”", '"')
            .replace("«", '"')
            .replace("»", '"')
            .replace("「", '"')
            .replace("」", '"')
            .replace("『", '"')
            .replace("』", '"')
    )

    # " ... " 구간 추출
    segments = re.findall(r'"([^"]+)"', normalized)

    for seg in segments:
        meaningful_chars = re.findall(r"[가-힣A-Za-z]", seg)
        if len(meaningful_chars) >= min_chars:
            return True

    return False


# -------------------------------------------------------------------
# 2. 기사 본문 수집
# -------------------------------------------------------------------

def get_article_content(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    개별 기사 페이지에서
      - 제목
      - 날짜 (YYYY.MM.DD)
      - 정제된 본문
    을 추출.
    """
    try:
        html = get_html(url)
        if not html:
            return None, None, None

        soup = BeautifulSoup(html, "html.parser")

        # 1) 제목
        title = None
        title_area = soup.find(id="title_area")
        if title_area:
            h2 = title_area.find("h2")
            title = (h2 or title_area).get_text(strip=True)
        else:
            h2 = soup.find("h2")
            if h2:
                title = h2.get_text(strip=True)

        # 2) 날짜
        date_tag = (
            soup.select_one(".media_end_head_info_datestamp_time")
            or soup.select_one("span.t11")
            or soup.select_one(".article_info .date")
        )
        raw_date = date_tag.get_text(strip=True) if date_tag else None
        date_str = extract_date_ymd(raw_date)

        # 3) 본문
        content_tag = soup.find(id="dic_area") or soup.find("article")
        content = clean_text(content_tag.get_text()) if content_tag else None

        if not title or not content:
            return None, None, None

        return title, date_str, content

    except Exception:
        return None, None, None


# -------------------------------------------------------------------
# 3. 필터 조건 (헤드라인 기준)
# -------------------------------------------------------------------

def check_conditions(title: str, content: str) -> bool:
    """
    필터 조건:
    1. 헤드라인(제목)에 직접 인용문이 있을 것
    2. 국내 경제/부동산 관련 키워드가 포함된 기사는 제외
    """
    if not title or not content:
        return False

    # 1) 제목에 직접 인용문(큰따옴표) 있어야 함
    if not has_direct_quote(title):
        return False

    # 2) 국내 경제/부동산 관련 키워드 제외
    exclude_keywords = [
        "부동산", "아파트", "전세", "월세", "청약", "분양",
        "재건축", "국토부", "LH", "집값", "공시가격",
        "코스피", "코스닥", "한국은행", "금융위", "금감원",
        "국내 경제", "우리나라 경제", "한국 경제", "전경련",
    ]

    full_text = f"{title} {content}"
    for kw in exclude_keywords:
        if kw in full_text:
            return False

    return True


# -------------------------------------------------------------------
# 4. 전체 크롤링 파이프라인
# -------------------------------------------------------------------

def crawl_world_articles(
    num_articles: int = 100,
    days_back: int = 90,
) -> pd.DataFrame:
    """
    세계(104) 섹션에서,
    - 날짜, 페이지를 순차적으로 훑어가며
    - 헤드라인에 직접 인용문이 있는 기사만
    - num_articles개 채워질 때까지 수집 후 즉시 종료.

    반환: DataFrame(columns=["category", "title", "date", "content", "url"])
    """
    data = {"category": [], "title": [], "date": [], "content": [], "url": []}
    collected_count = 0
    visited: set[str] = set()

    today = datetime.today()
    print(">>> 기사 수집 시작 (세계 섹션, 헤드라인 직접 인용문 필터)...")

    for d in range(days_back):
        if collected_count >= num_articles:
            break

        date = today - timedelta(days=d)
        date_str = date.strftime("%Y%m%d")
        page = 1

        while True:
            if collected_count >= num_articles:
                break

            list_url = (
                f"{BASE_URL}/main/list.naver"
                f"?mode=LSD&mid=shm&sid1={WORLD_SID1}"
                f"&date={date_str}&page={page}"
            )

            html = get_html(list_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            a_tags = soup.select(
                "a[href*='/mnews/article/'], a[href*='/read.naver']"
            )

            if not a_tags:
                break

            new_on_page = 0

            for a in a_tags:
                href = a.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = BASE_URL + href

                # 1) 섹션 필터: 실제로 sid=104 (세계)인 기사만
                if not is_world_section_url(href):
                    continue

                # 2) 중복 기사 건너뛰기
                if href in visited:
                    continue
                visited.add(href)

                # 3) 기사 파싱
                title, art_date, content = get_article_content(href)

                if title and content and check_conditions(title, content):
                    data["category"].append("세계")
                    data["title"].append(title)
                    data["date"].append(art_date)
                    data["content"].append(content)
                    data["url"].append(href)

                    collected_count += 1
                    new_on_page += 1

                    print(
                        f"[{collected_count}/{num_articles}] 저장 | "
                        f"{art_date} | {title[:40]}..."
                    )

                    if collected_count >= num_articles:
                        break

                time.sleep(0.1)

            # 이 페이지에서 새로 본 링크가 없다면 다음 페이지 의미 없음 → 종료
            if new_on_page == 0:
                break

            page += 1
            time.sleep(0.1)

        print(f"   [{date_str}] 탐색 완료. 누적 수집: {collected_count}개")

    df = pd.DataFrame(data)
    print(f"\n>>> 최종 수집 완료: {len(df)}개")
    return df


# -------------------------------------------------------------------
# 5. 모듈 단독 실행용 (옵션)
# -------------------------------------------------------------------

if __name__ == "__main__":
    df = crawl_world_articles(num_articles=10, days_back=30)

    if not df.empty:
        filename = "articles.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n파일 저장 완료: {filename}")
        print(df[["date", "title"]].head())
    else:
        print("\n조건에 맞는 데이터가 없습니다.")
