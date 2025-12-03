import pandas as pd
from tqdm import tqdm

from main import run_qdd2
from qdd2.translation import translate_ko_to_en
from qdd2.text_utils import extract_quotes


def build_dataset_from_articles(
    input_csv: str,
    text_col: str = "content",
    date_col: str = "date",          # 날짜 컬럼명
    output_csv: str | None = None,
    rollcall: bool = True,           # ← "트럼프일 때 rollcall 허용" 플래그
    span_top_k: int = 3,             # ← 인용문마다 원문 후보 TOP K개 추출
) -> pd.DataFrame:
    df_articles = pd.read_csv(input_csv)
    print("기사 컬럼:", df_articles.columns.tolist())

    records = []
    gid = 0  # quote 단위 global id

    for _, row in tqdm(df_articles.iterrows(), total=len(df_articles)):
        article_text = row.get(text_col, "")
        if not isinstance(article_text, str) or not article_text.strip():
            continue

        # 날짜
        article_date = row.get(date_col, None)

        # 인용문 추출: 헤드라인(title) + 본문(content) 둘 다에서 따옴표 추출
        quotes_ko: list[str] = []

        # 1) 헤드라인 인용문
        title_text = row.get("title", "")
        if isinstance(title_text, str) and title_text.strip():
            title_quotes = extract_quotes(title_text) or []
            quotes_ko.extend(title_quotes)

        # 2) 본문 인용문 (기존 로직)
        if isinstance(article_text, str) and article_text.strip():
            body_quotes = extract_quotes(article_text) or []
            quotes_ko.extend(body_quotes)

        # 3) 중복 제거
        quotes_ko = list(dict.fromkeys(q for q in quotes_ko if q))

        if not quotes_ko:
            continue


        # 기사 단위 트럼프 여부
        article_lower = article_text.lower()
        is_trump_article = (
            "트럼프" in article_text
            or "도널드 트럼프" in article_text
            or "donald trump" in article_lower
            or "president trump" in article_lower
        )

        for quote_ko in quotes_ko:
            gid += 1  # 인용문 하나당 id 1 증가

            quote_lower = str(quote_ko).lower()
            is_trump_quote = (
                "트럼프" in quote_ko
                or "도널드 트럼프" in quote_ko
                or "donald trump" in quote_lower
                or "president trump" in quote_lower
            )

            # rollcall=True로 build_dataset을 호출했을 때만,
            # 그리고 진짜 트럼프 문맥일 때만 rollcall 사용
            use_rollcall = rollcall and (is_trump_article or is_trump_quote)

            try:
                original_en = translate_ko_to_en(quote_ko)
            except Exception:
                original_en = None

            try:
                out = run_qdd2(
                    text=article_text,
                    file_path=None,
                    quote=quote_ko,
                    date=article_date,
                    top_n=15,
                    top_k=3,              # (키워드 관련 top_k; 기존 그대로 유지)
                    rollcall=use_rollcall,
                    top_k=3,
                    debug=False,
                    search=True,
                    top_matches=2,  # SBERT top-k 설정
                )
            except Exception as e:
                records.append(
                    {
                        "id": gid,               # 인용문 ID
                        "rank": None,            # 후보 순위
                        "original": quote_ko,
                        "original_en": original_en,
                        "source_quote_en": None,
                        "article_text": None,
                        "similarity": None,
                        "source_url": None,
                        "error": str(e),
                    }
                )
                continue

            # 1) run_qdd2에서 span 후보 리스트를 돌려준다고 가정
            #    예: out["span_candidates"] = [
            #         {"best_sentence": ..., "span_text": ..., "best_score": ..., "url": ...},
            #         {"best_sentence": ..., "span_text": ..., "best_score": ..., "url": ...},
            #         ...
            #       ]
            span_candidates = out.get("span_candidates") or []

            print("span_candidates 개수:", len(span_candidates), " / quote:", quote_ko[:30])

            # 후보 리스트가 없다면, 기존 best_span 하나만 쓰는 fallback
            if not span_candidates:
                best_span = out.get("best_span") or {}

                source_quote_en = (
                    best_span.get("best_sentence")
                    or best_span.get("sentence")
                    or best_span.get("span_text")
                )
                article_span_en = (
                    best_span.get("span_text")
                    or best_span.get("sentence")
                )
                sim_score = (
                    best_span.get("best_score")
                    or best_span.get("score")
                )
                source_url = best_span.get("url")

                records.append(
                    {
                        "id": gid,
                        "rank": 1,  # 유일한 후보
                        "original": quote_ko,
                        "original_en": original_en,
                        "source_quote_en": source_quote_en,
                        "article_text": article_span_en,
                        "similarity": sim_score,
                        "source_url": source_url,
                        "error": None,
                    }
                )
                continue

            # 2) span_candidates가 있으면, TOP K개까지 여러 row로 저장
            for rank, cand in enumerate(span_candidates[:span_top_k], start=1):
                source_quote_en = (
                    cand.get("best_sentence")
                    or cand.get("sentence")
                    or cand.get("span_text")
                )
                article_span_en = (
                    cand.get("span_text")
                    or cand.get("sentence")
                )
                sim_score = (
                    cand.get("best_score")
                    or cand.get("score")
                )
                source_url = cand.get("url")

                records.append(
                    {
                        "id": gid,                 # 인용문 ID (같음)
                        "rank": rank,              # 후보 순위 (1~K)
                        "original": quote_ko,
                        "original_en": original_en,
                        "source_quote_en": source_quote_en,
                        "article_text": article_span_en,
                        "similarity": sim_score,
                        "source_url": source_url,
                        "error": None,
                    }
                )

    df_out = pd.DataFrame(records)

    if output_csv is not None:
        df_out.to_csv(output_csv, index=False)

    return df_out


if __name__ == "__main__":
    INPUT_CSV = "articles.csv"
    OUTPUT_CSV = "out_dataset.csv"
    TEXT_COL = "content"
    DATE_COL = "date"

    df = build_dataset_from_articles(
        input_csv=INPUT_CSV,
        text_col=TEXT_COL,
        date_col=DATE_COL,
        output_csv=OUTPUT_CSV,
        rollcall=False,     # 트럼프 문맥이면 rollcall 사용
        span_top_k=5,      # 인용문 1개당 원문 후보
    )

    print("=== 데이터 생성 완료 ===")
    print(df.head())
    print(f"저장 경로: {OUTPUT_CSV}")
