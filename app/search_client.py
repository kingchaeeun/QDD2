"""
Google CSE client and page/PDF helpers.
"""

import os
import random
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin
from io import BytesIO

import pdfplumber
import requests

from qdd2 import config
from qdd2.text_utils import contains_korean

SESSION = requests.Session()
SESSION.headers.update(config.HTTP_HEADERS)


def is_valid_page(url: str, timeout: int = config.DEFAULT_TIMEOUT) -> bool:
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return False
        content_type = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return False
        return len((r.text or "").strip()) > config.HTML_MIN_LENGTH
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
    debug: bool = False,
):
    # Prefer environment variables; if none, fall back to config literals (as currently stored).
    api_key = os.getenv(config.GOOGLE_API_KEY_ENV) or (
        config.GOOGLE_API_KEY_ENV if config.GOOGLE_API_KEY_ENV and len(config.GOOGLE_API_KEY_ENV) > 20 else None
    )
    cse_cx = os.getenv(config.GOOGLE_CSE_CX_ENV) or (
        config.GOOGLE_CSE_CX_ENV if config.GOOGLE_CSE_CX_ENV and len(config.GOOGLE_CSE_CX_ENV) > 5 else None
    )
    assert api_key and cse_cx, "Set GOOGLE_API_KEY and GOOGLE_CSE_CX environment variables (or populate config values)"

    params = {
        "key": api_key,
        "cx": cse_cx,
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
            resp = SESSION.get(url, params=params, timeout=config.DEFAULT_TIMEOUT)
            if debug:
                print(f"[DEBUG] CSE attempt {attempt + 1}: {resp.status_code} -> {resp.url}")

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
    use_siteSearch: bool = True,  # kept for backward compatibility
    safe: Optional[str] = None,
    domain_list: Optional[List[str]] = None,
    debug: bool = False,
) -> List[Dict]:
    """
    Search across whitelisted domains and collect candidate pages.
    """
    candidates: List[Dict] = []
    seen = set()

    is_ko = contains_korean(query)
    lr = "lang_ko" if is_ko else None
    hl = "ko" if is_ko else "en"
    gl = "kr" if is_ko else "us"
    domains = domain_list if domain_list is not None else config.BASE_DOMAINS

    for site_filter in domains:
        sub_query = f"{query} {site_filter}"
        remaining = top_per_domain
        start = 1

        while remaining > 0:
            per_req = min(10, remaining)
            data = google_cse_search(
                q=sub_query,
                num=per_req,
                start=start,
                lr=lr,
                hl=hl,
                gl=gl,
                safe=safe,
                debug=debug,
            )
            items = data.get("items", []) or []
            if not items:
                break

            for it in items:
                url = it.get("link") or it.get("formattedUrl")
                if not url or url in seen:
                    continue
                if not is_valid_page(url):
                    continue

                candidates.append(
                    {
                        "domain": site_filter.replace("site:", ""),
                        "title": it.get("title", ""),
                        "url": url,
                        "snippet": it.get("snippet", ""),
                    }
                )
                seen.add(url)
                remaining -= 1
                if remaining == 0:
                    break

            start += per_req
            if start > 91:
                break
            time.sleep(0.2)

    return candidates


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_pdf_url_from_html(html: str, base_url: str) -> Optional[str]:
    """Extract PDF link from iframe/embed/a tags (useful for UN-style pages)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        src = iframe["src"]
        if ".pdf" in src.lower():
            return urljoin(base_url, src)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            return urljoin(base_url, href)

    return None


def extract_text_from_pdf_url(pdf_url: str) -> Optional[str]:
    """Download PDF and extract text with pdfplumber."""
    try:
        r = SESSION.get(pdf_url, timeout=config.PDF_TIMEOUT)
        if r.status_code != 200:
            print(f"[WARN] PDF request failed: {pdf_url}, status={r.status_code}")
            return None
    except Exception as e:
        print(f"[WARN] PDF request error: {pdf_url}, {e}")
        return None

    pdf_file = BytesIO(r.content)
    text_chunks: List[str] = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception as e:
        print(f"[WARN] PDF parsing error: {pdf_url}, {e}")
        return None

    text = "\n".join(text_chunks)
    text = re.sub(r"\s+", " ", text)
    try:
        text = bytes(text, "utf-8").decode("utf-8", "ignore")
    except Exception:
        pass

    return text.strip() or None
