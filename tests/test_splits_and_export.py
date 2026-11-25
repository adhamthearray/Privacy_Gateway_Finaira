import json
from collections import defaultdict

from common import DATA, QUESTION, read_jsonl


def test_grouped_splits_prevent_contrast_leakage():
    group_splits = defaultdict(set)
    for row in read_jsonl(DATA / "generated" / "entity_decisions.jsonl"):
        group_splits[row["contrast_group_id"]].add(row["split"])
    assert len(group_splits) == 16
    assert all(len(splits) == 1 for splits in group_splits.values())
    assert {next(iter(splits)) for splits in group_splits.values()} == {"train", "validation", "test"}


def test_unreviewed_official_exports_are_empty():
    for name in ["train", "validation", "test"]:
        assert read_jsonl(DATA / f"{name}.jsonl") == []


def test_question_contract_is_constant_and_three_class():
    criteria = QUESTION["entity_type_relevance"]["criteria"]
    assert set(criteria) == {"RELEVANT", "SEMI_RELEVANT", "IRRELEVANT"}
    assert "occurrence" in QUESTION["entity_type_relevance"]["instructions"]

