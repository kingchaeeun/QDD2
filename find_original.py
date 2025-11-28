import re
from typing import List, Dict, Tuple, Optional
from transformers import pipeline, MarianMTModel, MarianTokenizer
from keybert import KeyBERT
from direct_quote import split_sentences, clean_text # 의존성 Import

# ==========================================================
# 모델 로딩 (전역 변수 유지)
# ==========================================================

ner_pipe = pipeline(
    "ner",
    model="monologg/koelectra-base-v3-naver-ner",
    tokenizer="monologg/koelectra-base-v3-naver-ner",
    device=0,   # CPU (원본 코드 그대로)
)

# 키워드 추출용 KeyBERT (한국어 SBERT 기반)
kw_model = KeyBERT("snunlp/KR-SBERT-V40K-klueNLI-augSTS")

# 번역기 로딩 (Helsinki-NLP)
model_name = "Helsinki-NLP/opus-mt-ko-en"
trans_tokenizer = MarianTokenizer.from_pretrained(model_name)
trans_model = MarianMTModel.from_pretrained(model_name)


NER_LABELS = {
    "PER",  # 인물
    "ORG",  # 조직
    "LOC",  # 지역
    "DAT",  # 날짜
    "AFW",  # 인공물(건물, 시설)
}

RELATION_KEYWORDS = {
    "정상회담", "협력", "관계", "합의", "발표", "논의", "회담",
    "회동", "성명", "중재", "합동", "압박", "문제", "논란",
    "비판", "우려", "대응", "방침",
}

def normalize_korean_phrase(s: str) -> str:
    """
    중복 제거를 위한 정규화
    - 공백, 하이픈, 중점 등 제거
    - 한글/영문/숫자만 남김
    """
    s = re.sub(r"[·•ㆍ\-_/\s]", "", s)
    return s.lower()

def extract_quotes(text: str) -> List[str]:
    """쌍따옴표 안의 인용문 추출 (간단 버전)"""
    return re.findall(r'"([^"]+)"', text)

def merge_ner_entities(results, debug: bool = False):
    """연속된 BIO 태그를 하나의 엔티티로 병합"""
    if debug:
        print(f"    merge_ner_entities 입력: {len(results)}개")

    merged = []
    buffer = []

    for ent in results:
        if debug:
            print(f"      처리 중: {ent}")

        label = ent["entity"].split("-")
        entity_type = label[0]  # PER, ORG 등
        tag_type = label[1] if len(label) > 1 else "B"  # B, I

        if debug:
            print(f"        → tag_type={tag_type}, entity_type={entity_type}")

        # 관심 있는 엔티티 타입만
        if entity_type not in NER_LABELS:
            if debug:
                print(f"        → 스킵 (라벨 {entity_type}이 NER_LABELS에 없음)")
            continue

        if tag_type == "B":  # 새 엔티티 시작
            if buffer:
                merged.append(buffer)
            buffer = [ent]

        elif tag_type == "I" and buffer:  # 이전 엔티티 계속
            prev_type = buffer[-1]["entity"].split("-")[0]
            if entity_type == prev_type and ent["start"] <= buffer[-1]["end"] + 1:
                buffer.append(ent)
            else:
                merged.append(buffer)
                buffer = [ent]

        else:
            if buffer:
                merged.append(buffer)
            buffer = []

    if buffer:
        merged.append(buffer)

    if debug:
        print(f"    병합 후 그룹 수: {len(merged)}")

    final_entities = []
    for group in merged:
        entity_type = group[0]["entity"].split("-")[0]
        word = "".join([e["word"].replace("##", "") for e in group]).strip()

        # 필터링
        if not word or len(word) < 2:
            continue
        if word in {'"', "'", "(", ")", "[", "]", "{", "}", ",", ".", "!", "?"}:
            continue
        if word.replace(" ", "").replace("-", "").replace("·", "") == "":
            continue

        final_entities.append({"label": entity_type, "word": word})

        if debug:
            print(f"      → 최종 엔티티: {entity_type} = {word}")

    return final_entities


def extract_ner_entities(text: str, debug: bool = False) -> List[Dict]:
    """
    NER로 주요 엔티티 추출 (수동 병합)
    Returns: [{'label': 'PER', 'word': '트럼프'}, ...]
    """
    sentences = split_sentences(text)
    all_entities = []

    for i, sent in enumerate(sentences):
        raw_results = ner_pipe(sent)

        if debug:
            print(f"\n[문장 {i + 1}] {sent[:50]}...")
            print(f"  Raw NER 결과 개수: {len(raw_results)}")
            if raw_results:
                print(f"  첫 번째 결과 샘플: {raw_results[0]}")

        merged = merge_ner_entities(raw_results, debug=debug)

        if debug and merged:
            print(f"  병합된 엔티티: {merged}")

        all_entities.extend(merged)

    if debug:
        print(f"\n총 추출된 엔티티 수: {len(all_entities)}")

    return all_entities


def rerank_with_ner_boost(
    keywords: List[Tuple[str, float]],
    entities: List[Dict],
    text: str,
    alpha: float = 0.7,
    beta: float = 0.3,
) -> List[Tuple[str, float]]:
    """
    NER 엔티티와 관계어를 포함한 키워드에 가중치 부여
    """
    ent_terms = {normalize_korean_phrase(e["word"]) for e in entities}
    rel_terms = {normalize_korean_phrase(r) for r in RELATION_KEYWORDS}

    rescored = []
    for phrase, score in keywords:
        normalized = normalize_korean_phrase(phrase)

        has_entity = any(et in normalized for et in ent_terms)
        has_relation = any(rt in normalized for rt in rel_terms)

        bonus = 0.0
        if has_entity and has_relation:
            bonus = 1.0
        elif has_entity or has_relation:
            bonus = 0.6

        final_score = alpha * score + beta * bonus
        rescored.append((phrase, final_score))

    unique_keywords = {}
    for phrase, score in sorted(rescored, key=lambda x: x[1], reverse=True):
        key = normalize_korean_phrase(phrase)
        if key not in unique_keywords:
            unique_keywords[key] = (phrase, score)

    return sorted(unique_keywords.values(), key=lambda x: x[1], reverse=True)


def extract_keywords_with_ner(
    text: str,
    top_n: int = 15,
    use_mmr: bool = True,
    diversity: float = 0.7,
    alpha: float = 0.7,
    beta: float = 0.3,
    debug: bool = False,
) -> Dict:
    """
    KeyBERT + NER 기반 키워드 추출
    """

    # 1) NER 엔티티 추출
    entities = extract_ner_entities(text, debug=debug)

    # 2) KeyBERT로 기본 키워드 후보 추출
    if use_mmr:
        base_keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            top_n=top_n * 3,      # 후보 많이 뽑아두고
            use_mmr=True,
            diversity=diversity,
        )
    else:
        base_keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            top_n=top_n * 3,
            use_mmr=False,
        )
    # base_keywords: List[Tuple[str, float]]

    # 3) NER + 관계어 기반 재랭킹
    reranked_keywords = rerank_with_ner_boost(
        base_keywords,
        entities,
        text,
        alpha=alpha,
        beta=beta,
    )

    # 4) entities_by_type 구성 (기존 로직 유지)
    entities_by_type: Dict[str, List[str]] = {}
    seen_normalized = set()

    for ent in entities:
        label = ent["label"]
        word = ent["word"]
        normalized = normalize_korean_phrase(word)

        is_duplicate = False
        for seen in list(seen_normalized):
            # 더 긴 쪽만 남기기
            if normalized in seen and normalized != seen:
                is_duplicate = True
                break
            if seen in normalized and normalized != seen:
                # 이전에 넣었던 더 짧은 엔티티 제거
                seen_normalized.discard(seen)
                for lbl in entities_by_type:
                    entities_by_type[lbl] = [
                        w
                        for w in entities_by_type[lbl]
                        if normalize_korean_phrase(w) != seen
                    ]

        if not is_duplicate:
            seen_normalized.add(normalized)
            if label not in entities_by_type:
                entities_by_type[label] = []
            if word not in entities_by_type[label]:
                entities_by_type[label].append(word)

    return {
        "entities": entities,
        "keywords": reranked_keywords[:top_n],
        "entities_by_type": entities_by_type,
    }

def translate_ko_to_en(text: str) -> str:
    """문장 단위 한국어 → 영어 번역"""
    tokens = trans_tokenizer(text, return_tensors="pt", padding=True)
    translated = trans_model.generate(**tokens)
    return trans_tokenizer.decode(translated[0], skip_special_tokens=True)