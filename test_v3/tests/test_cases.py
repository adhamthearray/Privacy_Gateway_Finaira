import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_exactly_fifty_cases_and_requested_languages():
    rows = [json.loads(line) for line in (ROOT / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8") if line.strip()]
    assert len(rows) == 50
    assert {language: sum(row["language"] == language for row in rows) for language in ("ar", "mixed", "en")} == {"ar": 36, "mixed": 9, "en": 5}
    assert sum(bool(row["gold"]["verified_groups"]) for row in rows) == 30


def test_entity_offsets_are_unicode_codepoint_offsets():
    rows = [json.loads(line) for line in (ROOT / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8") if line.strip()]
    for row in rows:
        for entity in row["entities"]:
            assert row["document"][entity["start"]:entity["end"]] == entity["original"]


def test_arabic_cases_are_real_unicode_and_repeated_identity_is_annotated():
    rows = [json.loads(line) for line in (ROOT / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8") if line.strip()]
    arabic = next(row for row in rows if row["language"] == "ar")
    assert "العميل" in arabic["document"]
    repeated = [row for row in rows if any(entity["id"] == "bank-1-mention" for entity in row["entities"])]
    assert len(repeated) == 10
    bank_identity = next(entity["identity_key"] for entity in repeated[0]["entities"] if entity["id"] == "bank-1")
    assert {entity["identity_key"] for entity in repeated[0]["entities"] if entity["id"] == "bank-1-mention"} == {bank_identity}


def test_database_provenance_and_raw_value_exclusion_are_explicit():
    rows = [json.loads(line) for line in (ROOT / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8") if line.strip()]
    for row in rows:
        for entity in row["entities"]:
            assert entity["lookup"]["resolution_status"] in {"MATCHED", "VERIFIED"}
            assert entity["lookup"]["exact_candidate_id"]
            assert all(candidate["text"] != entity["original"] for candidate in entity["candidates"])
            assert all(candidate.get("metadata", {}).get("level_code") != "EXACT" for candidate in entity["candidates"])
