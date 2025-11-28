import os
import re
import time
import random
import requests
import torch
import pdfplumber
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

# 다른 모듈에서 함수 Import
from direct_quote import extract_span
from find_original import translate_ko_to_en
from per_name import get_wikidata_english_name

# ==========================================================
# 모델 및 세션 로딩
# ==========================================================

# 0-a) SPAN 매칭용 SentenceTransformer (유사도 전용)
sim_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

BASE_DOMAINS = [
    "site:whitehouse.gov",
    "site:congress.gov",
    "site:rollcall.com",
    "site:millercenter.org",
    "site:un.org",
        # 트럼프/미국 정치 연설·인터뷰 transcript 많이 있는 곳들
    "site:factba.se",
    "site:foxnews.com",
    "site:c-span.org",
    "site:abcnews.go.com",
    "site:nbcnews.com",
    "site:cnn.com",
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; QuoteContextBot/1.0; +https://example.org/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


def contains_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))

def is_valid_page(url: str, timeout: int = 12) -> bool:
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return False
        ct = (r.headers.get("Content-Type") or "").lower()
        if not ("text/html" in ct or "application/xhtml+xml" in ct):
            return False
        return len(r.text.strip()) > 500
    except requests.RequestException:
        return False

def google_cse_search(
    q: str,
    num: int = 10,
    start: int = 1,
    lr: Optional[str] = None,
    hl: str = "en",
    gl: str = "us",
    safe: Optional[str] = None,
    retries: int = 3,
    backoff: float = 1.4,
):
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_cx = os.getenv("GOOGLE_CSE_CX")
    assert google_api_key and google_cse_cx, "환경변수 GOOGLE_API_KEY / GOOGLE_CSE_CX 를 설정하세요."

    params = {
        "key": google_api_key,
        "cx": google_cse_cx,
        "q": q,
        "num": max(1, min(10, int(num))),
        "start": max(1, min(91, int(start))),
        "hl": hl,
        "gl": gl,
    }
    if lr:
        params["lr"] = lr
    if safe in ("active", "off"):
        params["safe"] = safe

    url = "https://www.googleapis.com/customsearch/v1"

    for attempt in range(retries):
        try:
            resp = SESSION.get(url, params=params, timeout=5)
                        # 🔍 여기서 실제 응답을 찍어보는 게 핵심
            print("\n[DEBUG] CSE 요청 시도:", attempt + 1)
            print("[DEBUG] status:", resp.status_code)
            print("[DEBUG] url:", resp.url)
            #print("[DEBUG] body 앞부분:", resp.text[:300])

            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                sleep_s = (backoff ** attempt) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                continue
            resp.raise_for_status()
        except requests.RequestException:
            sleep_s = (backoff ** attempt) + random.uniform(0, 0.25)
            time.sleep(sleep_s)
            continue

    return {"items": []}


def collect_candidates_google_cse(
    query: str,
    top_per_domain: int = 3,
    use_siteSearch: bool = True,
    safe: Optional[str] = None,
    domain_list: Optional[List[str]] = None,  # 🔹 추가
):
    """
    🔒 도메인 제한을 다시 적용한 버전
    → BASE_DOMAINS 리스트 안에 정의된 도메인만 검색
    """
    candidates = []
    seen = set()

    is_ko = contains_korean(query)
    lr = "lang_ko" if is_ko else None
    hl = "ko" if is_ko else "en"
    gl = "kr" if is_ko else "us"

     # 🔹 검색에 사용할 도메인 리스트 결정
    domains = domain_list if domain_list is not None else BASE_DOMAINS

    for site_filter in domains:   # ← 이 줄만 수정
        sub_query = f"{query} {site_filter}"
        want = top_per_domain
        start = 1

        while want > 0:
            per_req = min(10, want)

            data = google_cse_search(
                q=sub_query,
                num=per_req,
                start=start,
                lr=lr,
                hl=hl,
                gl=gl,
                safe=safe,
            )
            items = data.get("items", []) or []
            if not items:
                break

            for it in items:
                url = it.get("link") or it.get("formattedUrl")
                if not url or url in seen:
                    continue

                # site 필터를 만족하는 페이지인지 확인
                if not is_valid_page(url):
                    continue

                candidates.append({
                    "domain": site_filter.replace("site:", ""),
                    "title": it.get("title", ""),
                    "url": url,
                    "snippet": it.get("snippet", ""),
                })
                seen.add(url)
                want -= 1

                if want == 0:
                    break

            start += per_req
            if start > 91:
                break
            time.sleep(0.2)

    return candidates


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_into_sentences(text: str, is_ko: Optional[bool] = None) -> List[str]:
    """
    영어/한국어 모두에서 무난하게 쓸 수 있는 문장 분리기
    """
    if is_ko is None:
        is_ko = bool(re.search(r"[가-힣]", text))

    rough = re.split(r"(?<=[.!?])\s+", text)
    sentences = []

    for s in rough:
        s = s.strip()
        if not s:
            continue

        if is_ko:
            if len(s) < 10:
                continue
        else:
            if len(s) < 20:
                continue

        sentences.append(s)

    return sentences


def extract_pdf_url_from_html(html: str, base_url: str) -> Optional[str]:
    """UN 페이지처럼 PDF를 iframe/a로 embed한 경우 PDF 링크 추출"""
    soup = BeautifulSoup(html, "html.parser")

    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
         src = iframe["src"]
         # 진짜 PDF인 경우에만 PDF로 처리
         if ".pdf" in src.lower():
             return urljoin(base_url, src)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            return urljoin(base_url, href)

    return None


def extract_text_from_pdf_url(pdf_url: str) -> Optional[str]:
    """PDF URL에서 텍스트 추출"""
    try:
        r = SESSION.get(pdf_url, timeout=20)
        if r.status_code != 200:
            print(f"[WARN] PDF 요청 실패: {pdf_url}, status={r.status_code}")
            return None
    except Exception as e:
        print(f"[WARN] PDF 요청 에러: {pdf_url}, {e}")
        return None

    pdf_file = BytesIO(r.content)
    text_chunks = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception as e:
        print(f"[WARN] PDF 파싱 에러: {pdf_url}, {e}")
        return None

    text = "\n".join(text_chunks)
    text = re.sub(r"\s+", " ", text)

    try:
        text = bytes(text, "utf-8").decode("utf-8", "ignore")
    except Exception:
        pass

    return text.strip() or None


def semantic_similarity(text1: str, text2: str) -> float:
    """
    text1, text2를 같은 SentenceTransformer(sim_model)로 임베딩해서
    코사인 유사도 반환
    """
    with torch.no_grad():
        embeddings = sim_model.encode(
            [text1, text2],
            convert_to_tensor=True,
            normalize_embeddings=True,  # L2 정규화
        )
        emb1, emb2 = embeddings[0], embeddings[1]
        sim = util.cos_sim(emb1, emb2)  # shape: (1, 1)
        return float(sim.item())

def find_best_match_span_in_snippet(
    quote_text: str,
    snippet_text: str,
    url: str,
    num_before: int = 1,
    num_after: int = 1,
):
    """
    Google CSE 스니펫 텍스트 내에서 quote_text와 가장 유사한 문맥 Span을 찾는다.
    이 함수는 웹 페이지 전체를 로드하지 않아 속도가 매우 빠르다.
    """
    if not snippet_text:
        return None

    # 스니펫 텍스트를 문장 단위로 분리 (Span 후보)
    sentences = split_into_sentences(snippet_text, is_ko=False)

    if not sentences:
        return None

    n = len(sentences)

    # 1) 문장 단위 유사도 계산 (SBERT 배치 인코딩)
    try:
        with torch.no_grad():
            # (1) quote 하나만 인코딩
            quote_emb = sim_model.encode(
                [quote_text],
                convert_to_tensor=True,
                normalize_embeddings=True,
            )[0]  # (d,)

            # (2) 스니펫 문장 전체를 한 번에 인코딩
            sent_embs = sim_model.encode(
                sentences,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )  # (m, d)

            # (3) 코사인 유사도 벡터 (1 x m)
            sims = util.cos_sim(quote_emb, sent_embs)[0]  # (m,)

            best_local_idx = int(torch.argmax(sims).item())
            best_score = float(sims[best_local_idx].item())
    except Exception as e:
        print(f"[WARN] SBERT 인코딩/유사도 계산 에러: {e}")
        return None


    # 2) best_idx 기준으로 span 구성 (context용)
    # 스니펫이 짧으므로 num_before/num_after는 스니펫 내에서만 적용됨
    span_text, s_idx, e_idx = extract_span(
        sentences,
        best_local_idx,
        num_before=num_before,
        num_after=num_after,
        join_with=" ",
    )

    return {
        "url": url,
        "best_sentence": sentences[best_local_idx],
        "best_score": best_score,
        "span_text": span_text,
        "span_start_idx": s_idx,
        "span_end_idx": e_idx,
    }

def find_best_span_from_candidates_debug(
    quote_en: str,
    candidates: List[Dict],
    num_before: int = 1,
    num_after: int = 1,
    min_score: float=0.4,
):
    """
    여러 후보 URL(candidates)에 대해:
      - 각 URL에서 quote_en과 가장 유사한 span을 찾고
      - best_score가 min_score 이상인 것 중에서
      - 전역 최고 점수를 갖는 span 하나를 골라서 반환.

    반환 형식은 find_best_match_span_in_page와 동일:
      {
        "url": ...,
        "best_sentence": ...,
        "best_score": ...,
        "span_text": ...,
        "span_start_idx": ...,
        "span_end_idx": ...,
      }
    못 찾으면(None 또는 min_score 미만) → None
    """
    best_global = None

    for cand in candidates:
        url = cand.get("url")
        snippet = cand.get("snippet")
        if not url:
            continue

        try:
          # 💡 수정된 부분: 웹 페이지 전체 로드 대신 스니펫 사용
                span_res = find_best_match_span_in_snippet(
                quote_text=quote_en,
                snippet_text=snippet,
                url=url,
                num_before=num_before,
                num_after=num_after,
            )
        except Exception as e:
            print(f"[WARN] span 추출 중 에러 (url={url}, 스니펫 사용): {e}")
            continue

        if not span_res:
            continue

        score = span_res.get("best_score", -1.0)

        if score < min_score:
            # 유사도가 너무 낮으면 스킵
            continue

        if (best_global is None) or (score > best_global["best_score"]):
            best_global = span_res

    return best_global

def resolve_person_name_en(name_ko: str) -> str:
    """
    인물 이름 영어화:
    1) Wikidata에서 영어 라벨 찾기
    2) 실패하면 기계번역(ko→en)
    3) 번역도 실패하면 원문 그대로 반환
    """
    # 1) Wikidata
    info = get_wikidata_english_name(name_ko)
    if isinstance(info, dict) and info.get("en"):
        return info["en"]

    # 2) 번역 fallback
    try:
        return translate_ko_to_en(name_ko)
    except Exception:
        # 3) 최종 fallback: 그냥 한글 그대로
        return name_ko


def generate_search_query(
    entities_by_type: Dict[str, List[str]],
    keywords: List[Tuple[str, float]],
    top_k: int = 3,
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,   # 🔹 기사 날짜 (YYYY-MM-DD)
    rollcall_mode: bool = False,          # 🔹 rollcall.com 전용 모드
    use_wikidata: bool = True,
) -> Dict[str, Optional[str]]:

    """
    기본 모드:
      - PER: Wikidata or 번역 → 영어 이름
      - LOC: 개별 번역 후 한두 단어만 사용
      - 키워드: 개별 번역 후 짧게 사용
      - 인용문: 번역 후 **전체 문장** 사용

    rollcall_mode=True 일 때:
      - 검색 쿼리 = [발화자 영어] + [기사 날짜 영어] + [키워드 영어 1개]
    """

    # 1) PER (speaker)
    per_list = entities_by_type.get("PER", [])
    if not per_list:
        return {"ko": None, "en": None}

    speaker_ko = per_list[0]
    if use_wikidata:
        # Wikidata → 실패 시 번역까지 resolve_person_name_en 안에서 처리
        speaker_en = resolve_person_name_en(speaker_ko)
    else:
        # Wikidata 안 쓰겠다고 한 경우도 그냥 번역으로 처리
        try:
            speaker_en = translate_ko_to_en(speaker_ko)
        except Exception:
            speaker_en = speaker_ko


    # 2) LOC: 개별 번역 + 짧게 자르기
    loc_list = entities_by_type.get("LOC", [])[:2]
    locs_ko = " ".join(loc_list)

    locs_en_tokens: List[str] = []
    for loc in loc_list:
        try:
            loc_en_full = translate_ko_to_en(loc)  # ex) "Russia", "Ukraine"
            loc_en_first = loc_en_full.split(",")[0]  # 콤마 앞까지만
            loc_en_first = " ".join(loc_en_first.split()[:2])  # 단어 1~2개만
            if loc_en_first:
                locs_en_tokens.append(loc_en_first)
        except Exception:
            continue

    # 3) 키워드: 개별 번역 + 짧게
    top_kws_ko = [kw for kw, _ in keywords[:top_k]]
    kws_en_tokens: List[str] = []
    for kw_ko in top_kws_ko:
        try:
            kw_en_full = translate_ko_to_en(kw_ko)
            kw_en_trim = " ".join(kw_en_full.split()[:3])  # 앞 2~3단어만
            if kw_en_trim:
                kws_en_tokens.append(kw_en_trim)
        except Exception:
            continue


    # 4) 인용문: **전체 문장 사용**
    quote_en_full: Optional[str] = None
    if quote_sentence:
        try:
            quote_en_full = translate_ko_to_en(quote_sentence)
        except Exception:
            quote_en_full = None
        # rollcall.com 전용 모드
    if rollcall_mode and article_date:
        # 기사 날짜를 영어 포맷 (예: November 02 2025)로 변환
        try:
            dt = datetime.strptime(article_date, "%Y-%m-%d")
            date_en = dt.strftime("%B %d %Y")
        except Exception:
            date_en = article_date

        # 키워드 명사 하나: 여기서는 일단 가장 상위 키워드 1개 사용
        kw_ko_main = top_kws_ko[0] if top_kws_ko else ""
        kw_en_main = ""
        if kw_ko_main:
            try:
                kw_en_full = translate_ko_to_en(kw_ko_main)
                kw_en_main = kw_en_full.split()[0]  # 첫 단어만
            except Exception:
                kw_en_main = kw_ko_main

        parts_en = [speaker_en]
        if date_en:
            parts_en.append(date_en)
        if kw_en_main:
            parts_en.append(kw_en_main)

        query_en = " ".join(parts_en).strip()

        parts_ko = [speaker_ko]
        parts_ko.append(article_date)
        if kw_ko_main:
            parts_ko.append(kw_ko_main)
        query_ko = " ".join(parts_ko).strip()

        return {
            "ko": query_ko or None,
            "en": query_en or None,
        }
    # 여기까지 rollcall 모드, 아래는 기존 기본 모드

    # 5) EN 쿼리 토큰 합치기
    query_en_tokens: List[str] = [speaker_en]
    query_en_tokens += locs_en_tokens
    query_en_tokens += kws_en_tokens
    if quote_en_full:
        query_en_tokens.append(quote_en_full)

    query_en = " ".join(query_en_tokens).strip()

    # 6) KO 쿼리는 디버깅/로그용
    query_ko_parts = [speaker_ko]
    if locs_ko:
        query_ko_parts.append(locs_ko)
    if top_kws_ko:
        query_ko_parts.append(" ".join(top_kws_ko))
    if quote_sentence:
        query_ko_parts.append(quote_sentence)
    query_ko = " ".join(query_ko_parts).strip()

    return {
        "ko": query_ko or None,
        "en": query_en or None,
    }