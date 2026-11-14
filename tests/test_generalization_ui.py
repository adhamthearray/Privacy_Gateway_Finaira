from pathlib import Path

from scripts.run_generalization_ui import substring_suggestions


DB = Path("data/processed/finaira_generalization.db")


def test_ui_returns_review_only_substring_suggestions_for_arabic_job_text():
    suggestions = substring_suggestions(DB, "JOB_TITLE", "مدرسة", "en", limit=10)
    assert suggestions
    assert any("مدرسة" in item["alias_text"] for item in suggestions)
    assert all(item["review_required"] is True for item in suggestions)
    assert all(item["source"] == "ESCO substring suggestion" for item in suggestions)
