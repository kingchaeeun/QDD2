# direct_quote.py
# 기사 단: 인용문 추출 + 기사 내 span 유틸만 분리

import re
from typing import List


def split_sentences(text: str) -> List[str]:
    """문장 분리 (개선된 정규식, 주로 한국어용)"""
    text = re.sub(r"\s+", " ", text.strip())
    return re.split(r"(?<=[.!?])\s+(?=[가-힣A-Za-z])", text)


def extract_quotes_advanced(text: str) -> List[str]:
    """
    기사 본문 내에서 쌍따옴표로 둘러싸인 문장 모두 추출.
    대상: " ... " 또는 “ ... ”
    - 길이 6자 미만은 버림
    - 중복 제거 (등장 순서 유지)
    반환: 인용문 문자열 리스트 (없으면 빈 리스트)
    """
    patterns = [
        r"“([^”]+)”",
        r'"([^"]+)"',
    ]

    quotes: List[str] = []
    for pattern in patterns:
        quotes.extend(re.findall(pattern, text))

    # 전처리 & 최소 길이 필터
    quotes = [q.strip() for q in quotes if len(q.strip()) >= 6]

    # 중복 제거 (순서 유지)
    seen = set()
    unique_quotes = []
    for q in quotes:
        if q not in seen:
            seen.add(q)
            unique_quotes.append(q)

    return unique_quotes


def extract_span(
    sentences: List[str],
    center_idx: int,
    num_before: int = 1,
    num_after: int = 1,
    join_with: str = " ",
):
    n = len(sentences)
    if n == 0:
        raise ValueError("sentences 리스트가 비어 있습니다.")
    if not (0 <= center_idx < n):
        raise IndexError(f"center_idx {center_idx} 가 문장 길이 {n} 범위를 벗어남")

    start_idx = max(0, center_idx - num_before)
    end_idx = min(n - 1, center_idx + num_after)
    span = join_with.join(sentences[start_idx:end_idx + 1])

    return span, start_idx, end_idx
