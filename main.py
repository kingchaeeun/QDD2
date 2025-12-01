"""
Example CLI runner for the qdd2 pipeline.

Usage:
  python main.py --text '트럼프 "베네수엘라 상공 전면폐쇄"' --date 2024-11-29

Flags:
  --text / --file : input text (one must be provided)
  --quote         : specific quote sentence (optional; if omitted, pass None)
  --date          : article date YYYY-MM-DD (optional)
  --top-n         : number of keywords to extract (default 15)
  --top-k         : keywords used in the final query (default 3)
  --rollcall      : rollcall.com-friendly query mode (boolean flag)
  --debug         : verbose prints from NER/keyword extraction (boolean flag)
"""

import argparse
import logging
import sys

from qdd2.snippet_matcher import find_best_span_from_candidates_debug
from qdd2.translation import translate_ko_to_en
from qdd2.pipeline import build_queries_from_text
from qdd2.search_client import google_cse_search

def run_qdd2(
    text: str | None = None,
    file_path: str | None = None,
    quote: str | None = None,
    date: str | None = None,
    top_n: int = 15,
    top_k: int = 3,
    rollcall: bool = False,
    debug: bool = False,
    search: bool = False,
):
    """
    QDD2 파이프라인을 Python 함수로 호출할 수 있게 한 엔트리포인트.

    반환값 예시:
    {
        "pipeline_result": {...},          # build_queries_from_text 결과
        "search_items": [ {...}, ... ],    # CSE search items (search=True일 때만)
        "best_span": {...} or None,        # SBERT 기반 best span (search=True + 후보 있을 때만)
    }
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("qdd2.cli")

    logger.info("[Step 0] Starting QDD2 pipeline (function mode)")

    # 1) 텍스트 로딩
    if text is not None:
        loaded_text = text
    elif file_path is not None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_text = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {e}")
    else:
        raise ValueError("Either `text` or `file_path` must be provided.")

    logger.info("[Step 1] Loaded text (%d chars)", len(loaded_text))
    if quote:
        logger.info("Quote provided: %s", quote)
    if date:
        logger.info("Article date: %s", date)
    logger.info(
        "Args: top_n=%d, top_k=%d, rollcall=%s, debug=%s, search=%s",
        top_n, top_k, rollcall, debug, search,
    )

    # 2) 파이프라인 호출
    logger.info("[Step 2] Calling pipeline.build_queries_from_text()")
    result = build_queries_from_text(
        text=loaded_text,
        top_n_keywords=top_n,
        top_k_for_query=top_k,
        quote_sentence=quote,
        article_date=date,
        rollcall_mode=rollcall,
        device=0,  # CPU by default
        debug=debug,
    )
    logger.info("[Step 3] Pipeline completed")
    logger.info(
        "Summary: entities=%d, keywords=%d, queries(ko=%s / en=%s)",
        len(result.get("entities", [])),
        len(result.get("keywords", [])),
        bool(result.get("queries", {}).get("ko")),
        bool(result.get("queries", {}).get("en")),
    )

    # 3) (옵션) CSE 검색 + SBERT 기반 best span
    search_items: list[dict] = []
    best_span: dict | None = None

    if search:
        logger.info("[Step 4] Running Google CSE search with generated query")
        query = result["queries"].get("en") or result["queries"].get("ko")
        if not query:
            logger.warning("No query available to search.")
        else:
            data = google_cse_search(query, num=5, debug=debug)
            search_items = data.get("items", []) or []
            if not search_items:
                logger.warning("No results returned from CSE.")
            else:
                # --- 여기서부터 SBERT 유사도 기반 best span 계산 ---
                logger.info("[Step 5] Running SBERT snippet matching on CSE results")

                # 1) 유사도 계산에 사용할 영어 문장 결정
                quote_for_match_en: str | None = None

                if quote:
                    try:
                        quote_for_match_en = translate_ko_to_en(quote)
                    except Exception as e:
                        logger.warning("Quote translation failed, fallback to EN query: %s", e)

                if not quote_for_match_en:
                    # fallback: EN 쿼리 자체를 사용
                    quote_for_match_en = result["queries"].get("en")

                if quote_for_match_en:
                    candidates = []
                    for it in search_items:
                        url = it.get("link")
                        snippet = it.get("snippet", "") or ""
                        if not url or not snippet:
                            continue
                        candidates.append(
                            {
                                "url": url,
                                "snippet": snippet,
                            }
                        )

                    if candidates:
                        try:
                            best_span = find_best_span_from_candidates_debug(
                                quote_en=quote_for_match_en,
                                candidates=candidates,
                                num_before=1,
                                num_after=1,
                                min_score=0.2,  # threshold는 상황에 따라 조절 가능
                            )
                            if best_span:
                                logger.info(
                                    "[Step 6] Best span found: score=%.4f, url=%s",
                                    best_span.get("best_score", -1.0),
                                    best_span.get("url", ""),
                                )
                            else:
                                logger.warning("No span passed the similarity threshold.")
                        except Exception as e:
                            logger.warning("SBERT snippet matching failed: %s", e)
                else:
                    logger.warning("No English text available for similarity matching.")

    return {
        "pipeline_result": result,
        "search_items": search_items,
        "best_span": best_span,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QDD2 extraction/query test runner")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", type=str, help="Inline text to process")
    src.add_argument("--file", type=str, help="Path to a UTF-8 text file to process")

    parser.add_argument("--quote", type=str, default=None, help="Specific quote sentence (optional)")
    parser.add_argument("--date", type=str, default=None, help="Article date YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=15, help="Number of keywords to extract (default: 15)")
    parser.add_argument("--top-k", type=int, default=3, help="Keywords to include in query (default: 3)")
    parser.add_argument("--rollcall", action="store_true", help="Use rollcall.com-oriented query construction")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logs")
    parser.add_argument("--search", action="store_true", help="Automatically run Google CSE with the generated EN query")
    return parser.parse_args()


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read file {args.file}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()

    out = run_qdd2(
        text=args.text,
        file_path=args.file,
        quote=args.quote,
        date=args.date,
        top_n=args.top_n,
        top_k=args.top_k,
        rollcall=args.rollcall,
        debug=args.debug,
        search=args.search,
    )

    result = out["pipeline_result"]
    items = out["search_items"]

    print("\n=== Entities by type ===")
    for label, words in result["entities_by_type"].items():
        print(f"{label}: {words}")

    print("\n=== Top keywords ===")
    for kw, score in result["keywords"]:
        print(f"{kw}  ({score:.4f})")

    print("\n=== Queries ===")
    print(f"KO: {result['queries']['ko']}")
    print(f"EN: {result['queries']['en']}")

    if args.search and items:
        print("\n=== Top search results ===")
        for item in items[:5]:
            print(f"- {item.get('title', '').strip()} :: {item.get('link', '')}")

    best_span = out.get("best_span")

    if args.search and best_span:
        print("\n=== Best span by SBERT similarity ===")
        print(f"URL        : {best_span.get('url', '')}")
        print(f"SCORE      : {best_span.get('best_score', -1.0):.4f}")
        print(f"SENTENCE   : {best_span.get('best_sentence', '')}")
        print(f"SPAN TEXT  : {best_span.get('span_text', '')}")




if __name__ == "__main__":
    main()