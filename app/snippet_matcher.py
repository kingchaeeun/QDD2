"""
Snippet-level semantic matching helpers using SentenceTransformer.
"""

import re
from typing import Dict, List, Optional

import torch
from sentence_transformers import util

from qdd2.models import get_sentence_model
from qdd2.text_utils import contains_korean, clean_text

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
):
    """
    Use semantic similarity to find the best matching sentence span within a snippet.
    """
    if not snippet_text:
        return None

    sentences = split_into_sentences(snippet_text, is_ko=False)
    if not sentences:
        return None

    sim_model = get_sentence_model()
    try:
        with torch.no_grad():
            quote_emb = sim_model.encode(
                [quote_text],
                convert_to_tensor=True,
                normalize_embeddings=True,
            )[0]
            sent_embs = sim_model.encode(
                sentences,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )
            sims = util.cos_sim(quote_emb, sent_embs)[0]
            best_local_idx = int(torch.argmax(sims).item())
            best_score = float(sims[best_local_idx].item())
    except Exception as e:
        print(f"[WARN] SBERT similarity error: {e}")
        return None

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
    min_score: float = 0.4,
):
    """
    Iterate through candidate snippets, return the best-scoring span above threshold.
    """
    best_global = None
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
        if score < min_score:
            continue

        if (best_global is None) or (score > best_global["best_score"]):
            best_global = span_res

    return best_global
