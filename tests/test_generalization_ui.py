from pathlib import Path

from scripts.run_generalization_ui import substring_generalization, substring_suggestions


DB = Path("data/processed/finaira_generalization.db")


def test_ui_returns_review_only_substring_suggestions_for_arabic_job_text():
    suggestions = substring_suggestions(DB, "JOB_TITLE", "مدرسة", "en", limit=10)
    assert suggestions
    assert any("مدرسة" in item["alias_text"] for item in suggestions)
    assert all(item["review_required"] is True for item in suggestions)
    assert all(item["source"] == "ESCO substring suggestion" for item in suggestions)


def test_ui_substring_aggregation_is_safe_when_no_shared_isco_branch_exists():
    result = substring_generalization(DB, "JOB_TITLE", "مدرسة", "en")
    assert result["status"] == "NO_COMMON_ISCO_ANCESTOR"
    assert result["matched_occupation_count"] == 55
    assert [item["level_code"] for item in result["candidates"]] == ["SUPPRESSED"]


def test_ui_substring_aggregation_starts_at_shared_isco_ancestor():
    result = substring_generalization(DB, "JOB_TITLE", "human resources man", "en")
    assert result["status"] == "REVIEW_ONLY"
    assert result["common_isco_code"] == "1212"
    assert result["start_level"] == "ISCO_UNIT"
    assert [item["level_code"] for item in result["candidates"]] == ["ISCO_UNIT", "ISCO_MINOR", "ISCO_SUB_MAJOR", "ISCO_MAJOR"]
    assert all(item["is_exact"] is False for item in result["candidates"])
