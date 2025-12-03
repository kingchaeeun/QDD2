"""
Snippet-level semantic matching helpers using SentenceTransformer.
"""

import re
from typing import Dict, List, Optional

import torch
from sentence_transformers import util

# Prefer new quote_backend loaders; fall back to legacy app modules.
try:
    from quote_backend.models.loaders import get_sentence_model
    from quote_backend.utils.text_utils import contains_korean, clean_text
except ImportError:
    from app.models import get_sentence_model
    from app.text_utils import contains_korean, clean_text

# We keep split_into_sentences here to allow custom length thresholds for snippets.
def split_into_sentences(text: str, is_ko: Optional[bool] = None) -> List[str]:
    if is_ko is None:
        is_ko = contains_korean(text)

    rough = re.split(r"(?<=[.!?])\s+", text or "")
    sentences = []
    for s in rough:
        s = clean_text(s)
        if not s:
            continue
        if is_ko and len(s) < 10:
            continue
        if not is_ko and len(s) < 20:
            continue
        sentences.append(s)
    return sentences


def extract_span(sentences: List[str], center_idx: int, num_before: int = 1, num_after: int = 1, join_with: str = " "):
    n = len(sentences)
    if n == 0:
        raise ValueError("sentences list is empty")
    if not (0 <= center_idx < n):
        raise IndexError(f"center_idx {center_idx} is out of range for {n} sentences")

    start_idx = max(0, center_idx - num_before)
    end_idx = min(n - 1, center_idx + num_after)
    span = join_with.join(sentences[start_idx : end_idx + 1])
    return span, start_idx, end_idx


def find_best_match_span_in_snippet(
    quote_text: str,
    snippet_text: str,
    url: str,
    num_before: int = 1,
    num_after: int = 1,
) -> Optional[Dict]:
    """
    Use semantic similarity to find the best matching SPAN (문맥 포함 구간) within a snippet.

    변경 사항:
      - 인용문도 앞뒤 num_before/num_after 문장을 포함한 span으로 만든다.
      - snippet 쪽도 중심 문장 ± num_before/after span으로 만들고,
        quote_span vs snippet_span (SPAN-SPAN) 유사도를 비교한다.
    """
    if not snippet_text:
        return None

    # -----------------------------
    # 1) 인용문(quote_text) 쪽 span 만들기
    # -----------------------------
    # quote_text는 이미 영어(quote_en)라 가정 → is_ko=False
    quote_sentences = split_into_sentences(quote_text, is_ko=False)

    if quote_sentences:
        # 인용문 문장들 가운데 중심 문장 기준 span 생성
        center_idx_q = len(quote_sentences) // 2
        quote_span_text, _, _ = extract_span(
            quote_sentences,
            center_idx_q,
            num_before=num_before,
            num_after=num_after,
            join_with=" ",
        )
    else:
        # 문장 분리가 안 되면 전체를 하나의 span으로 사용
        quote_span_text = quote_text

    # -----------------------------
    # 2) snippet 쪽 span 후보들 만들기
    # -----------------------------
    sentences = split_into_sentences(snippet_text, is_ko=False)
    if not sentences:
        return None

    sim_model = get_sentence_model()
    try:
        with torch.no_grad():
            # 3) quote span 임베딩
            quote_emb = sim_model.encode(
                [quote_span_text],
                convert_to_tensor=True,
                normalize_embeddings=True,
            )[0]

            # 4) snippet 내 모든 candidate span 생성
            span_texts: List[str] = []
            span_meta: List[Dict] = []  # center_idx, start_idx, end_idx 저장

            n = len(sentences)
            for center_idx in range(n):
                span_text, s_idx, e_idx = extract_span(
                    sentences,
                    center_idx,
                    num_before=num_before,
                    num_after=num_after,
                    join_with=" ",
                )
                span_texts.append(span_text)
                span_meta.append(
                    {
                        "center_idx": center_idx,
                        "span_start_idx": s_idx,
                        "span_end_idx": e_idx,
                    }
                )

            # 5) 각 snippet span 임베딩
            span_embs = sim_model.encode(
                span_texts,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )

            # 6) quote_span vs snippet_span 유사도 (SPAN-SPAN)
            sims = util.cos_sim(quote_emb, span_embs)[0]
            best_idx = int(torch.argmax(sims).item())
            best_score = float(sims[best_idx].item())

    except Exception as e:
        print(f"[WARN] SBERT similarity error (span-span mode): {e}")
        return None

    # -----------------------------
    # 7) 베스트 span 정보 정리
    # -----------------------------
    best_span_text = span_texts[best_idx]
    meta = span_meta[best_idx]
    center_idx = meta["center_idx"]
    s_idx = meta["span_start_idx"]
    e_idx = meta["span_end_idx"]

    best_sentence = sentences[center_idx]  # 인터페이스 유지용

    return {
        "url": url,
        "best_sentence": best_sentence,   # 중심 문장
        "best_score": best_score,         # quote_span vs span_text 유사도
        "span_text": best_span_text,      # 실제 비교에 쓰인 span
        "span_start_idx": s_idx,
        "span_end_idx": e_idx,
    }



def find_best_span_from_candidates_debug(
    quote_en: str,
    candidates: List[Dict],
    num_before: int = 1,
    num_after: int = 1,
    min_score: float = 0.0,   # ★ threshold 거의 없애기
) -> Optional[Dict]:
    """
    Iterate through candidate snippets, collect ALL span candidates,
    and return:
      - best_global: 최고 점수 span (dict)
      - best_global["top_k_candidates"]: 점수 내림차순으로 정렬된 전체 후보 리스트

    주의:
      - min_score는 이제 "완전 쓰레기만 버리는 용도" 정도로만 사용하고,
        top_k_candidates에는 min_score와 상관없이 모든 후보를 넣는다.
    """

    global_candidates: List[Dict] = []

    for cand in candidates:
        url = cand.get("url")
        snippet = cand.get("snippet")
        if not url:
            continue

        try:
            span_res = find_best_match_span_in_snippet(
                quote_text=quote_en,
                snippet_text=snippet,
                url=url,
                num_before=num_before,
                num_after=num_after,
            )
        except Exception as e:
            print(f"[WARN] span extraction error (url={url}, snippet-based): {e}")
            continue

        if not span_res:
            continue

        score = span_res.get("best_score", -1.0)

        # ★ 모든 span 후보는 일단 다 모은다 (min_score와 무관)
        global_candidates.append(span_res)

    # 후보가 하나도 없으면 None
    if not global_candidates:
        return None

    # 점수 기준 내림차순 정렬
    sorted_candidates = sorted(
        global_candidates,
        key=lambda x: x.get("best_score", 0.0),
        reverse=True,
    )

    # 최고 점수 span = 맨 앞
    best_global = sorted_candidates[0]

    # ★ 여기서 전체 후보 리스트를 best_global에 붙여서 반환
    best_global["top_k_candidates"] = sorted_candidates

    # 필요하다면 여기서 min_score만 한 번 체크해서
    # 너무 낮으면 None을 돌려도 되지만,
    # 지금은 "후보는 일단 다 보고 싶다"는 목적이라 그냥 반환.
    return best_global
