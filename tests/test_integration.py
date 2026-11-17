from finaira.integration import NERPolicyJEVGateway
from finaira.policy_config import PolicyConfig


DB = "data/processed/finaira_generalization.db"


def _batch():
    return {
        "total_documents": 1,
        "completed_documents": 1,
        "handoffs": [
            {
                "document_id": "ner-doc-001",
                "text": "[[E1]] from [[E2]] paid [[E3]].",
                "entity_map": {
                    "E1": {"label": "PERSON_NAME", "original_text": "Alice Smith", "placeholder": "[[E1]]"},
                    "E2": {"label": "COUNTRY", "original_text": "Egypt", "placeholder": "[[E2]]"},
                    "E3": {"label": "MONETARY_AMOUNT", "original_text": "12500 SAR", "placeholder": "[[E3]]"},
                },
            }
        ],
    }


def test_batch_adapter_returns_policy_handoffs_and_jev_requests():
    result = NERPolicyJEVGateway(DB).prepare(_batch())

    assert result["total_documents"] == 1
    assert result["completed_documents"] == 1
    assert result["handoffs"][0]["entities"]["E1"]["pseudonymization_form"] == "__FN_PERSON_0001__"
    assert result["handoffs"][0]["entities"]["E2"]["effective_action"] == "GENERALIZE"
    assert result["handoffs"][0]["entities"]["E3"]["policy_action"] == "GENERALIZE"
    assert result["jev_handoff"]["protocol"] == "finaira-policy-to-jev-v1"
    request_ids = {item["request_id"] for item in result["jev_handoff"]["requests"]}
    assert request_ids == {"ner-doc-001:E2", "ner-doc-001:E3"}
    assert all(item["value"] for item in result["jev_handoff"]["requests"])
    assert all(item["selected_candidate"] is None for item in result["jev_handoff"]["requests"])


def test_jev_selection_can_be_applied_only_to_eligible_candidates():
    gateway = NERPolicyJEVGateway(DB)
    prepared = gateway.prepare(_batch())
    country = prepared["handoffs"][0]["entities"]["E2"]
    candidate = next(item for item in country["generalization_candidates"] if item["production_eligible"])

    result = gateway.apply_jev_selections(prepared, {"ner-doc-001:E2": candidate["candidate_id"]})
    selected = result["handoffs"][0]["entities"]["E2"]
    assert selected["effective_action"] == "GENERALIZE"
    assert selected["pseudonymization_form"] is None
    assert selected["generalization"]["selected_candidate"]["candidate_id"] == candidate["candidate_id"]
    assert selected["generalization"]["selected_replacement"] == candidate["representation"]
    assert result["jev_handoff"]["selections_applied"] == 1


def test_policy_actions_are_configurable_per_entity_type_and_id():
    config = PolicyConfig({"COUNTRY": "ALLOW"})
    gateway = NERPolicyJEVGateway(DB, policy_config=config)
    payload = {
        "document_id": "policy-override",
        "text": "[[E1]] [[E2]]",
        "policy_overrides": {"E2": "PSEUDONYMIZE"},
        "entity_map": {
            "E1": {"label": "COUNTRY", "original_text": "Egypt", "placeholder": "[[E1]]"},
            "E2": {"label": "COUNTRY", "original_text": "Egypt", "placeholder": "[[E2]]"},
        },
    }

    result = gateway.prepare(payload)
    assert result["entities"]["E1"]["policy_action"] == "ALLOW"
    assert result["entities"]["E1"]["pseudonymization_form"] is None
    assert result["entities"]["E2"]["policy_action"] == "PSEUDONYMIZE"
    assert result["entities"]["E2"]["pseudonymization_form"] == "__FN_COUNTRY_0001__"

