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

from qdd2.pipeline import build_queries_from_text
from qdd2.search_client import google_cse_search


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
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("qdd2.cli")

    logger.info("[Step 0] Starting QDD2 pipeline CLI")
    text = load_text(args)
    logger.info("[Step 1] Loaded text (%d chars)", len(text))
    if args.quote:
        logger.info("Quote provided: %s", args.quote)
    if args.date:
        logger.info("Article date: %s", args.date)
    logger.info("Args: top_n=%d, top_k=%d, rollcall=%s, debug=%s, search=%s", args.top_n, args.top_k, args.rollcall, args.debug, args.search)

    logger.info("[Step 2] Calling pipeline.build_queries_from_text()")
    result = build_queries_from_text(
        text=text,
        top_n_keywords=args.top_n,
        top_k_for_query=args.top_k,
        quote_sentence=args.quote,
        article_date=args.date,
        rollcall_mode=args.rollcall,
        device=0,  # CPU by default
        debug=args.debug,
    )
    logger.info("[Step 3] Pipeline completed")
    logger.info(
        "Summary: entities=%d, keywords=%d, queries(ko=%s / en=%s)",
        len(result.get("entities", [])),
        len(result.get("keywords", [])),
        bool(result.get("queries", {}).get("ko")),
        bool(result.get("queries", {}).get("en")),
    )

    print("\n=== Entities by type ===")
    for label, words in result["entities_by_type"].items():
        print(f"{label}: {words}")

    print("\n=== Top keywords ===")
    for kw, score in result["keywords"]:
        print(f"{kw}  ({score:.4f})")

    print("\n=== Queries ===")
    print(f"KO: {result['queries']['ko']}")
    print(f"EN: {result['queries']['en']}")

    if args.search:
        logger.info("[Step 4] Running Google CSE search with generated query")
        query = result["queries"].get("en") or result["queries"].get("ko")
        if not query:
            logger.warning("No query available to search.")
            return
        data = google_cse_search(query, num=5, debug=args.debug)
        items = data.get("items", []) or []
        if not items:
            logger.warning("No results returned from CSE.")
        else:
            print("\n=== Top search results ===")
            for item in items[:5]:
                print(f"- {item.get('title', '').strip()} :: {item.get('link', '')}")


if __name__ == "__main__":
    main()
