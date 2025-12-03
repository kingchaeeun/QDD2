"""
NER helpers: run pipeline, merge BIO tokens, and return cleaned entities.
"""

from typing import Dict, List, Sequence

from quote_backend.config import DEFAULT_DEVICE, NER_LABELS
from quote_backend.models.loaders import get_ner_pipeline
from quote_backend.utils.text_utils import split_sentences


def merge_ner_entities(results: Sequence[Dict], debug: bool = False) -> List[Dict]:
    """
    Merge BIO-tagged pieces from the transformer NER output into full entities.
    
    Args:
        results: Sequence of NER token results
        debug: Enable debug output
        
    Returns:
        List of merged entities with label and word
    """
    merged_groups = []
    buffer = []

    for ent in results:
        raw_label = str(ent.get("entity") or "")
        parts = raw_label.split("-")

        # Robustly parse HuggingFace-style BIO tags.
        # Typical shapes:
        #   - "B-PER", "I-ORG"  (naver-ner, etc.)
        #   - "PER-B", "ORG-I"  (older conventions)
        #   - "PER"             (no BIO prefix)
        entity_type = ""
        tag_type = "B"

        if len(parts) == 2:
            left, right = parts[0], parts[1]
            if left in {"B", "I"} and right in NER_LABELS:
                # "B-PER" → tag_type=B, entity_type=PER
                tag_type, entity_type = left, right
            elif right in {"B", "I"} and left in NER_LABELS:
                # "PER-B" → tag_type=B, entity_type=PER
                tag_type, entity_type = right, left
            else:
                # Fallback: keep previous behavior
                entity_type, tag_type = left, right
        elif len(parts) == 1:
            # No BIO info, treat as beginning of entity
            entity_type = parts[0]
            tag_type = "B"
        else:
            # Unexpected format – skip
            entity_type = parts[0] if parts else ""
            tag_type = "B"

        if entity_type not in NER_LABELS:
            if debug:
                print(f"Skipping non-target label: {entity_type}")
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


def extract_ner_entities(text: str, device: int = DEFAULT_DEVICE, debug: bool = False) -> List[Dict]:
    """
    Run NER over each sentence and merge tokens into clean entities.
    
    Args:
        text: Input text to process
        device: Device index (0 for CPU, >0 for GPU)
        debug: Enable debug output
        
    Returns:
        List of entities with label and word: [{'label': 'PER', 'word': '...'}, ...]
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

