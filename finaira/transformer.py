from .models import Entity


def transform_document(document: str, replacements: list[tuple[Entity, str]]) -> str:
    spans: list[tuple[int, int, str]] = []
    for entity, replacement in replacements:
        if entity.start is None or entity.end is None:
            raise ValueError("MISSING_SPAN")
        if not (0 <= entity.start < entity.end <= len(document)):
            raise ValueError("INVALID_SPAN")
        if document[entity.start:entity.end] != entity.original_value:
            raise ValueError("SPAN_VALUE_MISMATCH")
        spans.append((entity.start, entity.end, replacement))
    spans.sort()
    for previous, current in zip(spans, spans[1:]):
        if current[0] < previous[1]:
            raise ValueError("OVERLAPPING_SPANS")
    for start, end, replacement in reversed(spans):
        document = document[:start] + replacement + document[end:]
    return document
