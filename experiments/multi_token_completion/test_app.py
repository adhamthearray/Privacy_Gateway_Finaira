import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import app


def test_parse_multi_entity_spec():
    specs = app._parse_specs(
        "Alice used Bank",
        "",
        "OTHER",
        1,
        True,
        '[{"entity_id":"E1","span":"Alice","entity_type":"PERSON_NAME"}]',
    )
    assert specs == [{"entity_id": "E1", "span": "Alice", "entity_type": "PERSON_NAME", "occurrence": 1}]


def test_parse_multi_entity_rejects_invalid_json():
    with pytest.raises(ValueError, match="MULTI_ENTITY_JSON_INVALID"):
        app._parse_specs("text", "", "OTHER", 1, True, "not-json")


class _FakeGenerator:
    method_name = "FAKE_BASELINE"
    official_ss_mtc = False

    def generate(self, document, span, entity_type, **kwargs):
        replacement = "REPLACEMENT_" + entity_type
        return {
            "document": document,
            "selected_span": span,
            "entity_type": entity_type,
            "candidates": [{
                "rank": 1,
                "replacement": replacement,
                "log_score": -1.0,
                "reconstructed_text": document.replace(span, replacement, 1),
                "entity_type_consistency": "NOT_VERIFIED",
                "broader_than_original": "NOT_VERIFIED",
                "privacy_safety": "NOT_ASSESSED",
                "warnings": [],
            }],
        }


def test_generate_returns_multi_entity_json_and_export(monkeypatch):
    monkeypatch.setattr(app, "GENERATOR", _FakeGenerator())
    result = app.generate(
        "Alice used National Bank of Egypt.",
        "",
        "OTHER",
        1,
        "auto",
        "fake-checkpoint",
        1,
        "fixed",
        2,
        "cpu",
        True,
        json.dumps([
            {"entity_id": "E0001", "span": "Alice", "entity_type": "PERSON_NAME"},
            {"entity_id": "E0002", "span": "National Bank of Egypt", "entity_type": "BANK"},
        ]),
        False,
    )

    assert "Generated 2 candidate(s)" in result[0]
    assert result[2] == "REPLACEMENT_PERSON_NAME used REPLACEMENT_BANK."
    assert result[4]["mode"] == "MULTI_ENTITY"
    assert len(result[4]["results"]) == 2
    assert Path(result[5]).exists()
    Path(result[5]).unlink()
