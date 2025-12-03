"""
Integration test for the real /analyze-article pipeline (no stubs).

This script:
  - Loads the sample HTML from tests/sample_articles/naver_trump_comfort_women.html
  - Calls the FastAPI route function directly
  - Prints a compact summary of the first few (quote, candidate) pairs
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from quote_backend.api.main import AnalyzeArticleRequest, AnalyzeArticleResponse, analyze_article


async def _run() -> None:
    html_path = Path("tests/sample_articles/naver_trump_comfort_women.html")
    if not html_path.is_file():
        raise SystemExit(f"HTML file not found: {html_path}")

    html = html_path.read_text(encoding="utf-8")

    request = AnalyzeArticleRequest(article_html=html)
    response: AnalyzeArticleResponse = await analyze_article(request)

    print("AnalyzeArticleResponse (summary):")
    print(f"- total results: {len(response.results)}")
    for row in response.results[:5]:
        print(
            f"  quote_id={row.quote_id} "
            f"sim={row.similarity_score:.2f} "
            f"dist={row.distortion_score:.2f} "
            f"url={row.candidate_link}"
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

