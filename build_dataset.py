# build_dataset.py

import pandas as pd
from tqdm import tqdm

from main import run_qdd2
from qdd2.translation import translate_ko_to_en
from qdd2.text_utils import extract_quotes  # ← 실제 함수명에 맞게 수정


def build_dataset_from_articles(
    input_csv: str,
    text_col: str = "content",
    output_csv: str | None = None,
    rollcall: bool = False,
) -> pd.DataFrame:
    """
    크롤링된 기사 CSV를 읽어서 인용문 단위로 원문 + 유사도까지 뽑아서
    id, original, original_en, source_quote_en, article_text, similarity, source_url
    형태의 DataFrame/CSV를 생성한다.
    """
    df_articles = pd.read_csv(input_csv)
    print("기사 컬럼:", df_articles.columns.tolist())

    records = []
    gid = 0

    for _, row in tqdm(df_articles.iterrows(), total=len(df_articles)):
        article_text = row.get(text_col, "")
        if not isinstance(article_text, str) or not article_text.strip():
            continue

        # 1) QDD2 text_utils 기반 인용문 추출
        quotes_ko = extract_quotes(article_text)
        if not quotes_ko:
            continue

        # 2) 각 인용문마다 QDD2 파이프라인 실행
        for quote_ko in quotes_ko:
            gid += 1

            try:
                # 한국어 인용문 → 영어 번역 (데이터셋 컬럼용)
                original_en = translate_ko_to_en(quote_ko)
            except Exception:
                original_en = None

            try:
                out = run_qdd2(
                    text=article_text,
                    file_path=None,
                    quote=quote_ko,
                    date=None,          # 지금 CSV에 날짜 없으니 None
                    top_n=15,
                    top_k=3,
                    rollcall=rollcall,
                    debug=False,
                    search=True,        # CSE + SBERT 유사도까지 사용
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
                }
            )

    df_out = pd.DataFrame(records)

    if output_csv is not None:
        df_out.to_csv(output_csv, index=False)

    return df_out


# -------------------------------
# PyCharm에서 Run 버튼 한 번으로 실행
# -------------------------------
if __name__ == "__main__":
    INPUT_CSV = "articles.csv"
    OUTPUT_CSV = "out_dataset.csv"      # 결과 파일 이름
    TEXT_COL = "content"                # 기사 본문 컬럼명 (중요)

    df = build_dataset_from_articles(
        input_csv=INPUT_CSV,
        text_col=TEXT_COL,
        output_csv=OUTPUT_CSV,
        rollcall=True,   # rollcall 전용 쿼리 쓰고 싶으면 True
    )

    print("=== 데이터 생성 완료 ===")
    print(df.head())
    print(f"저장 경로: {OUTPUT_CSV}")
