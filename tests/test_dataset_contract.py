from collections import Counter, defaultdict

from common import DATA, ENTITY_TYPES, LABELS, LANGUAGES, read_jsonl


def test_exact_scope_and_pilot_size():
    prompts = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    decisions = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    assert len(prompts) == 144
    assert len(decisions) == 1440
    assert {row["target_entity_type"] for row in decisions} == set(ENTITY_TYPES)
    assert {row["proposed_label"] for row in decisions} == set(LABELS)


def test_every_prompt_has_complete_type_sweep():
    groups = defaultdict(list)
    for row in read_jsonl(DATA / "generated" / "entity_decisions.jsonl"):
        groups[row["prompt_id"]].append(row)
    assert all(len(rows) == 10 for rows in groups.values())
    assert all({row["target_entity_type"] for row in rows} == set(ENTITY_TYPES) for rows in groups.values())


def test_every_type_label_language_cell_is_covered():
    coverage = Counter(
        (row["target_entity_type"], row["proposed_label"], row["language_code"])
        for row in read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    )
    assert all(coverage[(entity, label, language)] > 0 for entity in ENTITY_TYPES for label in LABELS for language in LANGUAGES)


def test_synthetic_rows_are_not_gold():
    decisions = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    assert all(row["approved_gold_label"] is None for row in decisions)
    assert all(row["annotation_status"] == "PENDING_REVIEW" for row in decisions)

