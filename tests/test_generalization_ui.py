import json
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path

from scripts.run_generalization_ui import HTML, Handler, substring_generalization, substring_suggestions


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


def _query_ui(params):
    Handler.db_path = DB
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/query?{urlencode(params)}"
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ui_date_query_exposes_detector_and_contextual_generalization():
    ambiguous = _query_ui({"value": "03/04/2026", "type": "DATE", "language": "en"})
    assert ambiguous["resolution_status"] == "AMBIGUOUS"
    assert ambiguous["date_detection"]["reason_code"] == "AMBIGUOUS_DATE"

    resolved = _query_ui({"value": "03/04/2026", "type": "DATE", "language": "en", "date_order": "DMY"})
    assert resolved["resolution_status"] == "VERIFIED"
    assert resolved["date_detection"]["date_iso"] == "2026-04-03"
    assert [item["level_code"] for item in resolved["candidates"]] == ["EXACT", "MONTH", "QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]


def test_ui_date_query_supports_relative_and_non_gregorian_context():
    relative = _query_ui({"value": "tomorrow", "type": "DATE", "language": "en", "anchor_date": "2026-11-14"})
    assert relative["date_detection"]["date_iso"] == "2026-11-15"
    assert relative["date_detection"]["is_relative"] is True

    hijri = _query_ui({"value": "١٤ رمضان ١٤٤٨ هـ", "type": "DATE", "language": "ar"})
    assert hijri["date_detection"]["calendar"] == "HIJRI"
    assert hijri["date_detection"]["date_iso"] is None
    assert hijri["candidates"][0]["taxonomy"] == "HIJRI"


def test_ui_contains_date_context_controls():
    for control in ("date-context", "date-format", "date-order", "date-calendar", "date-hint", "anchor-date", "two-digit-year-base"):
        assert f'id="{control}"' in HTML
    assert 'id="language"' not in HTML


def test_ui_detects_input_language_and_returns_bilingual_nationality_labels():
    result = _query_ui({"value": "سوري", "type": "NATIONALITY", "language": "en"})
    assert result["input_language"] == "ar"
    assert result["resolution_status"] == "MATCHED"
    assert result["canonical_id"] == "Q858"
    exact = result["candidates"][0]
    assert exact["label_en"]
    assert exact["label_ar"]
    assert result["final_decision"]["action"] == "GENERALIZE"


def test_ui_bank_model_exact_candidate_uses_approved_arabic_alias():
    result = _query_ui({"value": "\u0628\u0646\u0643 \u0642\u0646\u0627\u0629 \u0627\u0644\u0633\u0648\u064a\u0633", "type": "BANK"})
    assert result["canonical_id"] == "BANK_SUEZ_CANAL_BANK"
    assert result["resolution_status"] == "REVIEW_ONLY"
    exact = next(item for item in result["candidates"] if item["level_code"] == "EXACT")
    assert exact["label_en"] == "Suez Canal Bank"
    assert exact["label_ar"] == "\u0628\u0646\u0643 \u0642\u0646\u0627\u0629 \u0627\u0644\u0633\u0648\u064a\u0633"
    assert result["final_decision"]["reason_code"] == "DIRECT_MATCH_REVIEW_GATED"
    assert result["final_decision"]["match_method"] == "DIRECT_MATCH_REVIEW_GATED"
    assert result["final_decision"]["matched_count"] == 1


def test_ui_review_only_corporation_explains_direct_match_gate():
    result = _query_ui({"value": "Ain Shams University", "type": "UNIVERSITY"})
    assert result["resolution_status"] == "REVIEW_ONLY"
    assert result["canonical_id"] == "Q2723670"
    assert result["final_decision"]["reason_code"] == "DIRECT_MATCH_REVIEW_GATED"
    assert result["final_decision"]["match_method"] == "DIRECT_MATCH_REVIEW_GATED"
    assert result["final_decision"]["matched_count"] == 1


def test_ui_exposes_final_decision_for_all_generalizable_entity_types():
    cases = [
        ("JOB_TITLE", "technical director", "en", "GENERALIZE"),
        ("COUNTRY", "Egypt", "en", "GENERALIZE"),
        ("NATIONALITY", "Egyptian", "en", "GENERALIZE"),
        ("BANK", "Emirates NBD Bank", "en", "GENERALIZE"),
        ("AGE", "27", "en", "GENERALIZE"),
        ("DATE", "2026-03-14", "en", "GENERALIZE"),
    ]
    for entity_type, value, language, expected_action in cases:
        result = _query_ui({"value": value, "type": entity_type, "language": language})
        assert result["final_decision"]["action"] == expected_action, entity_type
        assert result["final_decision"]["final_response"]
        assert result["final_decision"]["why"]


def test_ui_final_decision_uses_common_ancestor_or_pseudonymizes():
    common = _query_ui({"value": "human resources man", "type": "JOB_TITLE", "language": "en"})
    assert common["final_decision"]["action"] == "GENERALIZE"
    assert common["final_decision"]["reason_code"] == "SUBSTRING_COMMON_ANCESTOR"
    assert common["final_decision"]["common_ancestor"] == "1212"
    assert common["final_decision"]["final_response"] == "Managers"

    no_match = _query_ui({"value": "not a real entity", "type": "CORPORATION", "language": "en"})
    assert no_match["final_decision"]["action"] == "PSEUDONYMIZE"
    assert no_match["final_decision"]["reason_code"] == "NO_MATCH"
    assert no_match["final_decision"]["final_response"] == "PSEUDONYMIZE_REQUIRED"

    ambiguous_date = _query_ui({"value": "8/6/2024", "type": "DATE", "language": "en"})
    assert ambiguous_date["final_decision"]["action"] == "PSEUDONYMIZE"
    assert ambiguous_date["final_decision"]["reason_code"] == "AMBIGUOUS_DATE"
