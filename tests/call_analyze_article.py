"""
Simple local tester for the /analyze-article endpoint.

Usage:
  1) Start the backend:
       python run_server.py
  2) In another terminal, run:
       python tests/call_analyze_article.py
"""

from __future__ import annotations

import json
from pathlib import Path

import requests


def main() -> None:
  base_url = "http://127.0.0.1:8000"
  endpoint = f"{base_url}/analyze-article"

  html_path = Path("tests/sample_articles/naver_trump_comfort_women.html")
  if not html_path.is_file():
    raise SystemExit(f"HTML file not found: {html_path}")

  html = html_path.read_text(encoding="utf-8")

  resp = requests.post(
    endpoint,
    json={"article_html": html},
    timeout=600,  # allow long first-run model downloads
  )

  print("Status:", resp.status_code)
  try:
    data = resp.json()
  except json.JSONDecodeError:
    print("Non-JSON response:")
    print(resp.text[:1000])
    return

  # Pretty-print a compact summary (first few results)
  results = data.get("results", [])
  print(f"Total (quote, candidate) pairs: {len(results)}")
  for row in results[:5]:
    print(
      f"- quote_id={row.get('quote_id')} "
      f"sim={row.get('similarity_score'):.2f} "
      f"dist={row.get('distortion_score'):.2f} "
      f"url={row.get('candidate_link')}"
    )


if __name__ == "__main__":
  main()


