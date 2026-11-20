from __future__ import annotations

from typing import Any, Mapping

from .ladder import candidate_texts


def render_document(case: Mapping[str, Any], selection: Mapping[str, int], ladders: Mapping[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Render right-to-left using original Unicode-codepoint offsets."""
    entities = sorted(case["entities"], key=lambda item: (int(item["start"]), int(item["end"])))
    by_identity: dict[str, str] = {}
    texts = {
        entity["id"]: (entity["original"] if int(selection[entity["id"]]) < 0 else candidate_texts(ladders, selection)[entity["id"]])
        for entity in entities
    }
    for entity in entities:
        key = str(entity.get("identity_key") or entity["id"])
        by_identity.setdefault(key, texts[entity["id"]])
    rendered = case["document"]
    spans: dict[str, dict[str, Any]] = {}
    for entity in reversed(entities):
        start, end = int(entity["start"]), int(entity["end"])
        key = str(entity.get("identity_key") or entity["id"])
        replacement = by_identity[key]
        rendered = rendered[:start] + replacement + rendered[end:]
    # Re-find each replacement in rendered order. This avoids offset arithmetic
    # errors when Arabic and repeated identities change string length.
    cursor = 0
    for entity in entities:
        key = str(entity.get("identity_key") or entity["id"])
        replacement = by_identity[key]
        found = rendered.find(replacement, cursor)
        if found < 0:
            raise ValueError(f"RENDERED_ENTITY_NOT_FOUND:{entity['id']}")
        spans[entity["id"]] = {"start": found, "end": found + len(replacement), "text": replacement, "identity_key": key}
        cursor = found + len(replacement)
    return {"text": rendered, "entity_spans": spans, "selected_text": by_identity}
