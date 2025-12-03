"""
Example CLI runner for the app pipeline.

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
  --search        : run web search + span matching
"""

import argparse
import logging
import sys

try:
    from quote_backend.core.pipeline import build_queries_from_text
    from quote_backend.utils.translation import translate_ko_to_en
    from quote_backend.services.search_service import SearchService
    # Import legacy modules for compatibility
    from app.snippet_matcher import find_best_span_from_candidates_debug
    from app.search_client import google_cse_search
    from app.rollcall_search import get_search_results
    from app.trump_utils import detect_trump_context
except ImportError:
    # Fallback to old imports
    from app.snippet_matcher import find_best_span_from_candidates_debug
    from app.translation import translate_ko_to_en
    from app.pipeline import build_queries_from_text
    from app.search_client import google_cse_search
    from app.rollcall_search import get_search_results
    from app.trump_utils import detect_trump_context

def run_app(
    text: str | None = None,
    file_path: str | None = None,
    quote: str | None = None,
    date: str | None = None,
    top_n: int = 15,
    top_k: int = 3,
    rollcall: bool = False,
    debug: bool = False,
    search: bool = False,
    top_matches: int = 1,  # ★ 추가
):
    def get_top_k_spans(
        quote_en: str,
        candidates: list[dict],
        k: int,
        num_before: int = 1,
        num_after: int = 1,
        min_score: float = 0.2,
    ):
        results = []
        for c in candidates:
            span = find_best_span_from_candidates_debug(
                quote_en=quote_en,
                candidates=[c],
                num_before=num_before,
                num_after=num_after,
                min_score=min_score,
            )
            if span:
                results.append(span)

        results = sorted(results, key=lambda x: x.get("best_score", 0), reverse=True)
        return results[:k]

    """
    app 파이프라인을 Python 함수로 호출할 수 있게 한 엔트리포인트.

    반환값 예시:
    {
        "pipeline_result": {...},          # build_queries_from_text 결과
        "search_items": [ {...}, ... ],    # 검색 결과 아이템 (search=True일 때만)
        "best_span": {...} or None,        # SBERT 기반 best span (search=True + 후보 있을 때만)
    }
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("app.cli")

    logger.info("[Step 0] Starting app pipeline (function mode)")

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
    quote_text = quote or ""

    # 3-A) NER 기반 트럼프 감지
    is_trump_context = detect_trump_context(
        article_text=loaded_text,
        quote_text=quote,
        pipeline_result=result,
    )

    logger.info("Trump context detected: %s", is_trump_context)

    # 4) (옵션) 검색 + SBERT 기반 best span
    search_items: list[dict] = []
    best_span: dict | None = None
    span_candidates: list[dict] = []  # ★ 추가: 후보 span 리스트

    if search:
        logger.info("[Step 4] Running search with generated query")

        # 쿼리는 EN → KO 우선 사용
        query = result["queries"].get("en") or result["queries"].get("ko")

        if not query:
            logger.warning("No query available to search.")
        else:
            # 4-A) 트럼프 컨텍스트 + rollcall=True → Rollcall 우선, 실패 시 CSE
            if is_trump_context and rollcall:
                logger.info("[Search] Trump context + rollcall=True → using Rollcall Selenium search first")
                try:
                    rollcall_links = get_search_results(query, top_k=5)
                except Exception as e:
                    logger.warning("Rollcall search failed, fallback to CSE: %s", e)
                    rollcall_links = []

                search_items = [
                    {"link": url, "snippet": ""}
                    for url in rollcall_links
                    if url
                ]

                if not search_items:
                    logger.info("[Search] No rollcall results, fallback to Google CSE")
                    data = google_cse_search(query, num=20, debug=debug)
                    search_items = data.get("items", []) or []

            # 4-B) 그 외에는 무조건 CSE 사용
            else:
                logger.info("[Search] Using Google CSE (non-Trump context or rollcall=False)")
                data = google_cse_search(query, num=5, debug=debug)
                search_items = data.get("items", []) or []

        if not search_items:
            logger.warning("No results returned from search backends.")
        else:
            # --- 여기서부터 SBERT 유사도 기반 best span 계산 ---
            logger.info("[Step 5] Running SBERT snippet matching on search results")

            # 1) 유사도 계산에 사용할 영어 문장 결정
            quote_for_match_en: str | None = None

            if quote_text:
                try:
                    quote_for_match_en = translate_ko_to_en(quote_text)
                except Exception as e:
                    logger.warning("Quote translation failed, fallback to EN query: %s", e)

            if not quote_for_match_en:
                # fallback: EN 쿼리 자체를 사용
                quote_for_match_en = result["queries"].get("en")

            if quote_for_match_en:
                candidates = []
                for it in search_items:
                    url = it.get("link")
                    if not url:
                        continue
                    snippet = it.get("snippet", "") or ""
                    candidates.append(
                        {
                            "url": url,
                            "snippet": snippet,
                        }
                    )

                if candidates:
                    try:
                        top_spans = get_top_k_spans(
                            quote_en=quote_for_match_en,
                            candidates=candidates,
                            k=top_matches,
                            num_before=1,
                            num_after=1,
                            min_score=0.2,
                        )
                        best_span = top_spans[0] if top_spans else None
                        if best_span:
                            logger.info(
                                "[Step 6] Best span found: score=%.4f, url=%s",
                                best_span.get("best_score", -1.0),
                                best_span.get("url", ""),
                            )
                            # ★ 추가: snippet_matcher에서 넣어준 후보 리스트 꺼내기
                            span_candidates = best_span.get("top_k_candidates", []) or []
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
        "span_candidates": span_candidates,  # ★ 추가

    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="app extraction/query test runner")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", type=str, help="Inline text to process")
    src.add_argument("--file", type=str, help="Path to a UTF-8 text file to process")

    parser.add_argument("--quote", type=str, default=None, help="Specific quote sentence (optional)")
    parser.add_argument("--date", type=str, default=None, help="Article date YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=15, help="Number of keywords to extract (default: 15)")
    parser.add_argument("--top-k", type=int, default=3, help="Keywords to include in query (default: 3)")
    parser.add_argument("--rollcall", action="store_true", help="Use rollcall.com-oriented query construction")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logs")
    parser.add_argument("--search",action="store_true",help="Automatically run web search (Rollcall for Trump context, otherwise Google CSE)")
    parser.add_argument("--top-matches",type=int,default=1,help="Number of top similarity spans to return (default: 1)")

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

    out = run_app(
        text=args.text,
        file_path=args.file,
        quote=args.quote,
        date=args.date,
        top_n=args.top_n,
        top_k=args.top_k,
        rollcall=args.rollcall,
        debug=args.debug,
        search=args.search,
        top_matches=args.top_matches,   # ★ 추가
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

    if args.search and out.get("top_spans"):
        print("\n=== Top SBERT similarity spans ===")
        for i, span in enumerate(out["top_spans"], 1):
            print(f"\n# {i}")
            print(f"URL        : {span.get('url', '')}")
            print(f"SCORE      : {span.get('best_score', -1.0):.4f}")
            print(f"SENTENCE   : {span.get('best_sentence', '')}")
            print(f"SPAN TEXT  : {span.get('span_text', '')}")


if __name__ == "__main__":
    main()
