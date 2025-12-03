import pandas as pd
from tqdm import tqdm

from main import run_app
from app.translation import translate_ko_to_en
from app.text_utils import extract_quotes  # ← 실제 함수명에 맞게 수정


def build_dataset_from_articles(
    input_csv: str,
    text_col: str = "content",
    date_col: str = "date",          # 날짜 컬럼명
    output_csv: str | None = None,
    rollcall: bool = True,           # ← "트럼프일 때 rollcall 허용" 플래그
) -> pd.DataFrame:
    df_articles = pd.read_csv(input_csv)
    print("기사 컬럼:", df_articles.columns.tolist())

    records = []
    gid = 0

    for _, row in tqdm(df_articles.iterrows(), total=len(df_articles)):
        article_text = row.get(text_col, "")
        if not isinstance(article_text, str) or not article_text.strip():
            continue

        # 날짜
        article_date = row.get(date_col, None)

        # 인용문 추출
        quotes_ko = extract_quotes(article_text)
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
            gid += 1

            quote_lower = str(quote_ko).lower()
            is_trump_quote = (
                "트럼프" in quote_ko
                or "도널드 트럼프" in quote_ko
                or "donald trump" in quote_lower
                or "president trump" in quote_lower
            )

            # 🔴 여기서 정확히 정의
            # rollcall=True로 build_dataset을 호출했을 때만,
            # 그리고 진짜 트럼프 문맥일 때만 rollcall 사용
            use_rollcall = rollcall and (is_trump_article or is_trump_quote)

            try:
                original_en = translate_ko_to_en(quote_ko)
            except Exception:
                original_en = None

            try:
                out = run_app(
                    text=article_text,
                    file_path=None,
                    quote=quote_ko,
                    date=article_date,
                    top_n=15,
                    top_k=3,
                    rollcall=use_rollcall,   # ← 이제 정의돼 있음
                    debug=False,
                    search=True,
                )
            except Exception as e:
                records.append(
                    {
                        "id": gid,
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

            best_span = out.get("best_span") or {}

            source_quote_en = best_span.get("best_sentence")
            article_span_en = best_span.get("span_text")
            sim_score = best_span.get("best_score")
            source_url = best_span.get("url")

            records.append(
                {
                    "id": gid,
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
        rollcall=True,   # 트럼프 문맥이면 rollcall 사용
    )

    print("=== 데이터 생성 완료 ===")
    print(df.head())
    print(f"저장 경로: {OUTPUT_CSV}")
