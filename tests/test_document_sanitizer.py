import json
from pathlib import Path

import pytest

from finaira import prepare_document


DB = "data/processed/finaira_generalization.db"


def test_challenging_example_is_based_on_current_database_and_policy():
    payload = json.loads(Path("examples/document_sanitizer_challenging_sample.json").read_text(encoding="utf-8"))
    result = prepare_document(payload, DB)

    assert result["summary"] == {
        "pseudonymize_count": 2,
        "generalize_count": 9,
        "allow_count": 1,
        "selection_performed": False,
    }
    assert result["entities"]["E0003"]["generalization"]["status"] == "REVIEW_ONLY"
    assert result["entities"]["E0007"]["generalization"]["status"] == "VERIFIED"
    assert result["entities"]["E0008"]["generalization"]["status"] == "AMBIGUOUS"
    assert result["entities"]["E0010"]["policy_action"] == "GENERALIZE"
    assert result["entities"]["E0010"]["monetary_result"]["interpretation"]["normalized_amount"] == "12500"
    assert result["entities"]["E0012"]["generalization"]["status"] == "NOT_FOUND"


def test_monetary_amount_is_generalized_with_three_unselected_options():
    request = {
        "document_id": "doc-money",
        "text": "The amount is [[E1]].",
        "entity_map": {
            "E1": {
                "label": "MONETARY_AMOUNT",
                "original_text": "١٢٫٥ ألف ريال سعودي",
                "placeholder": "[[E1]]",
                "context": {"currency": "SAR"},
            }
        },
    }

    result = prepare_document(request, DB)
    entity = result["entities"]["E1"]

    assert entity["policy_action"] == "GENERALIZE"
    assert entity["pseudonymization_form"] is None
    assert entity["generalization"]["runtime_entity_type"] == "MONETARY_AMOUNT"
    assert entity["generalization"]["selected_candidate"] is None
    assert entity["monetary_result"]["interpretation"]["normalized_amount"] == "12500"
    assert [item["level_code"] for item in entity["generalization_candidates"]] == [
        "RANGE_BASED",
        "ORDER_OF_MAGNITUDE",
        "TASK_AWARE_THRESHOLD",
    ]
    assert entity["generalization_candidates"][0]["production_eligible"] is True
    assert entity["generalization_candidates"][2]["missing_reason"] == "REQUIRES_THRESHOLD"


def test_generalization_without_a_production_candidate_falls_back_to_counter_pseudonym():
    request = {
        "document_id": "doc-fallbacks",
        "text": "[[E1]] [[E1]] [[E2]]",
        "entity_map": {
            "E1": {
                "label": "DATE",
                "original_text": "03/04/2026",
                "placeholder": "[[E1]]",
            },
            "E2": {
                "label": "CORPORATION",
                "original_text": "Unknown Holdings",
                "placeholder": "[[E2]]",
            },
        },
    }

    result = prepare_document(request, DB)
    date_entity = result["entities"]["E1"]
    corporation = result["entities"]["E2"]

    assert date_entity["generalization"]["status"] == "AMBIGUOUS"
    assert date_entity["effective_action"] == "PSEUDONYMIZE"
    assert date_entity["pseudonymization_form"] == "__FN_DATE_0001__"
    assert date_entity["fallback_reason"] == "NO_PRODUCTION_GENERALIZATION_CANDIDATE"
    assert corporation["generalization"]["status"] == "NOT_FOUND"
    assert corporation["effective_action"] == "PSEUDONYMIZE"
    assert corporation["pseudonymization_form"] == "__FN_CORPORATION_0001__"


def test_placeholder_document_returns_pseudonym_forms_without_echoing_originals():
    request = {
        "document_id": "doc-001",
        "text": "[[E0001]] emailed [[E0002]]. [[E0001]] requested a refund.",
        "entity_map": {
            "E0001": {
                "label": "PERSON_NAME",
                "original_text": "Ahmed Ali",
                "placeholder": "[[E0001]]",
            },
            "E0002": {
                "label": "EMAIL_ADDRESS",
                "original_text": "ahmed@example.com",
                "placeholder": "[[E0002]]",
            },
        },
    }

    result = prepare_document(request, DB)

    assert result["document_id"] == "doc-001"
    assert result["text"] == request["text"]
    assert result["summary"] == {
        "pseudonymize_count": 2,
        "generalize_count": 0,
        "allow_count": 0,
        "selection_performed": False,
    }
    assert result["entities"]["E0001"]["pseudonymization"]["form"] == "__FN_PERSON_0001__"
    assert result["entities"]["E0002"]["pseudonymization"]["form"] == "__FN_EMAIL_0001__"
    assert result["entities"]["E0001"]["pseudonymization_form"] == "__FN_PERSON_0001__"
    assert result["entities"]["E0002"]["pseudonymization_form"] == "__FN_EMAIL_0001__"
    assert result["entities"]["E0001"]["generalization_candidates"] == []
    serialized = str(result)
    assert "Ahmed Ali" not in serialized
    assert "ahmed@example.com" not in serialized


def test_generalization_entity_returns_candidates_without_selecting_one():
    request = {
        "document_id": "doc-country",
        "text": "The customer is from [[E0001]].",
        "entity_map": {
            "E0001": {
                "label": "COUNTRY",
                "original_text": "Egypt",
                "placeholder": "[[E0001]]",
            }
        },
    }

    result = prepare_document(request, DB)
    entity = result["entities"]["E0001"]

    assert entity["policy_action"] == "GENERALIZE"
    assert entity["pseudonymization"] is None
    assert entity["generalization"]["status"] == "MATCHED"
    assert entity["generalization"]["selected_candidate"] is None
    assert entity["generalization"]["requires_selection"] is True
    assert any(item["level_code"] == "CONTINENT" for item in entity["generalization_candidates"])
    assert all("production_eligible" in item for item in entity["generalization_candidates"])


def test_organization_like_labels_keep_source_kind_but_use_corporation_runtime():
    request = {
        "document_id": "doc-org",
        "text": "[[E0001]]",
        "entity_map": {
            "E0001": {
                "label": "UNIVERSITY",
                "original_text": "Ain Shams University",
                "placeholder": "[[E0001]]",
            }
        },
    }

    result = prepare_document(request, DB)
    entity = result["entities"]["E0001"]

    assert entity["source_entity_type"] == "UNIVERSITY"
    assert entity["canonical_entity_type"] == "CORPORATION"
    assert entity["generalization"]["runtime_entity_type"] == "CORPORATION"
    assert entity["generalization"]["status"] == "REVIEW_ONLY"
    assert any(item["verification_status"] == "PENDING_IDENTITY_VALIDATION" for item in entity["generalization_candidates"])


@pytest.mark.parametrize(
    "payload, error",
    [
        ({"document_id": "x", "text": "hello", "entity_map": {}}, None),
        ({"document_id": "x", "text": "hello", "entity_map": {"E1": {"label": "PERSON_NAME", "original_text": "A", "placeholder": "[[E1]]"}}}, "PLACEHOLDER_NOT_FOUND:E1"),
    ],
)
def test_placeholder_validation(payload, error):
    if error:
        with pytest.raises(ValueError, match=error):
            prepare_document(payload, DB)
    else:
        assert prepare_document(payload, DB)["entities"] == {}

