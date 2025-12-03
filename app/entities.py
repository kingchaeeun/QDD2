"""
NER helpers: run pipeline, merge BIO tokens, and return cleaned entities.
"""

from typing import Dict, List, Sequence

from app import config
from app.models import get_ner_pipeline
from app.text_utils import split_sentences


def merge_ner_entities(results: Sequence[Dict], debug: bool = False) -> List[Dict]:
    """
    Merge BIO-tagged pieces from the transformer NER output into full entities.
    """
    merged_groups = []
    buffer = []

    for ent in results:
        raw_label = str(ent.get("entity") or "")
        parts = raw_label.split("-")

        # HuggingFace nav er-ner style: "B-PER", "I-ORG" 등 다양한 포맷을 안전하게 처리
        entity_type = ""
        tag_type = "B"

        if len(parts) == 2:
            left, right = parts[0], parts[1]
            if left in {"B", "I"} and right in config.NER_LABELS:
                # "B-PER" → tag_type=B, entity_type=PER
                tag_type, entity_type = left, right
            elif right in {"B", "I"} and left in config.NER_LABELS:
                # "PER-B" → tag_type=B, entity_type=PER
                tag_type, entity_type = right, left
            else:
                # 예상치 못한 포맷: 이전 동작과 최대한 비슷하게 유지
                entity_type, tag_type = left, right
        elif len(parts) == 1:
            entity_type = parts[0]
            tag_type = "B"
        else:
            entity_type = parts[0] if parts else ""
            tag_type = "B"

        if entity_type not in config.NER_LABELS:
            if debug:
                print(f"Skipping non-target label: {entity_type} (raw={raw_label})")
            continue

        if tag_type == "B":
            if buffer:
                merged_groups.append(buffer)
            buffer = [ent]
        elif tag_type == "I" and buffer:
            prev_type = (buffer[-1]["entity"] or "").split("-")[0]
            if entity_type == prev_type and ent["start"] <= buffer[-1]["end"] + 1:
                buffer.append(ent)
            else:
                merged_groups.append(buffer)
                buffer = [ent]
        else:
            if buffer:
                merged_groups.append(buffer)
            buffer = []

    if buffer:
        merged_groups.append(buffer)

    entities: List[Dict] = []
    for group in merged_groups:
        entity_type = (group[0]["entity"] or "").split("-")[0]
        word = "".join([str(e.get("word", "")).replace("##", "") for e in group]).strip()

        if len(word) < 2:
            continue
        if word in {'"', "'", "(", ")", "[", "]", "{", "}", ",", ".", "!", "?"}:
            continue
        if word.replace(" ", "").replace("-", "").replace("·", "") == "":
            continue

        entities.append({"label": entity_type, "word": word})
        if debug:
            print(f"Merged entity: {entity_type} -> {word}")

    return entities


def extract_ner_entities(text: str, device: int = config.DEFAULT_DEVICE, debug: bool = False) -> List[Dict]:
    """
    Run NER over each sentence and merge tokens into clean entities.
    Returns: [{'label': 'PER', 'word': '...'}, ...]
    """
    sentences = split_sentences(text)
    ner = get_ner_pipeline(device=device)
    all_entities: List[Dict] = []

    for idx, sentence in enumerate(sentences):
        raw = ner(sentence)
        merged = merge_ner_entities(raw, debug=debug)
        all_entities.extend(merged)

        if debug:
            print(f"[Sentence {idx + 1}] {sentence[:80]}...")
            print(f"  Raw: {len(raw)} -> Merged: {len(merged)}")

    return all_entities
