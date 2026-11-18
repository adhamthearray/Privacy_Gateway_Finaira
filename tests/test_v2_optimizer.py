import json

import pytest

from finaira.v2 import V2Optimizer, build_real_examples, exhaustive_optimum, make_golden_fixture


def _selected(result):
    return {item["entity_id"]: item["text"] for item in result["selected_candidates"]}


def test_real_examples_are_policy_generalizable_and_exact_direct():
    examples = build_real_examples()
    assert "real_arabic_exact_direct" in examples
    request = next(iter(examples.values()))
    optimizer = V2Optimizer()
    prepared, _, _ = optimizer.prepare(request)

    assert {entity.entity_type for entity in prepared.entities} == {"AGE", "JOB_TITLE", "BANK", "NATIONALITY"}
    for entity in prepared.entities:
        assert entity.lookup["mode"] == "database_exact_direct"
        assert entity.lookup["direct_match"] is True
        assert entity.lookup["resolution_status"] in {"MATCHED", "VERIFIED"}
        assert all(candidate.text != entity.original for candidate in entity.candidates)
        assert any(candidate.terminal_pseudonym for candidate in entity.candidates)
        assert all(candidate.metadata.get("lookup_source") == "database_exact_direct" for candidate in entity.candidates if not candidate.terminal_pseudonym)


def test_exhaustive_small_case_matches_milp_objective():
    optimizer = V2Optimizer()
    request = make_golden_fixture()
    exact = exhaustive_optimum(optimizer, request, max_utility_loss=1)
    milp = optimizer.v2_milp(request, max_utility_loss=1)
    assert exact["status"] == milp["status"] == "FEASIBLE"
    assert exact["specificity"] == pytest.approx(milp["metrics"]["total_specificity"])
    assert exact["utility_loss"] == pytest.approx(milp["metrics"]["total_utility_loss"])


def test_golden_u_max_1_matches_required_result():
    result = V2Optimizer().compare(make_golden_fixture(), max_utility_loss=1)
    assert result["baseline"]["metrics"]["total_utility_loss"] == 0
    assert result["baseline"]["metrics"]["total_specificity"] == pytest.approx(1.4)
    assert result["v2"]["status"] == "FEASIBLE"
    assert _selected(result["v2"]) == {
        "age": "__FN_AGE_0001__",
        "job": "IT Professional",
        "location": "Egypt",
    }
    assert result["v2"]["metrics"]["total_utility_loss"] == pytest.approx(1)
    assert result["v2"]["metrics"]["total_specificity"] == pytest.approx(1.0)
    assert result["evaluation"]["structural_disclosure_reduction_pct"] == pytest.approx(28.5714)


def test_golden_u_max_2_uses_job_category_and_location_pseudonym():
    result = V2Optimizer().v2_milp(make_golden_fixture(), max_utility_loss=2)
    assert result["status"] == "FEASIBLE"
    assert _selected(result) == {
        "age": "__FN_AGE_0001__",
        "job": "IT Professional",
        "location": "__FN_LOCATION_0001__",
    }
    assert result["metrics"]["total_specificity"] == pytest.approx(0.8)


def test_forbidden_original_and_unmatched_value_fall_back_to_typed_pseudonym():
    request = {
        "case_id": "case-unmatched",
        "task": "professional_summary",
        "document": "Customer nationality is Zzzland.",
        "entities": [{"id": "n1", "type": "NATIONALITY", "original": "Zzzland", "start": 24, "end": 31}],
    }
    result = V2Optimizer().v2_milp(request, max_utility_loss=10)
    assert result["status"] == "FEASIBLE"
    selected = result["selected_candidates"][0]
    assert selected["candidate"]["terminal_pseudonym"] is True
    assert selected["text"] == "__FN_NATIONALITY_0001__"
    assert "Zzzland" not in selected["text"]


def test_bank_pseudonyms_reuse_exact_identity_and_separate_other_bank():
    document = "Emirates NBD Bank approved it. Mashreq Bank reviewed it. Emirates NBD Bank confirmed it."
    first = document.find("Emirates NBD Bank")
    second = document.find("Mashreq Bank")
    third = document.rfind("Emirates NBD Bank")
    request = {
        "case_id": "case-banks",
        "task": "professional_summary",
        "document": document,
        "entities": [
            {"id": "b1", "type": "BANK", "original": "Emirates NBD Bank", "start": first, "end": first + 17},
            {"id": "b2", "type": "BANK", "original": "Mashreq Bank", "start": second, "end": second + 12},
            {"id": "b3", "type": "BANK", "original": "Emirates NBD Bank", "start": third, "end": third + 17},
        ],
    }
    optimizer = V2Optimizer()
    request_obj, _, tokens = optimizer.prepare(request)
    assert tokens["b1"] == tokens["b3"]
    assert tokens["b1"] != tokens["b2"]
    assert all(any(candidate.terminal_pseudonym for candidate in entity.candidates) for entity in request_obj.entities)

    second_case = optimizer.prepare({**request, "case_id": "case-banks-2"})[2]
    assert second_case["b1"] == "__FN_BANK_0001__"
    assert second_case is not tokens


def test_existing_direct_placeholder_is_preserved_and_counter_avoids_collision():
    request = {
        "case_id": "case-direct-placeholder",
        "task": "customer_demographic_summary",
        "document": "Customer __FN_PERSON_0001__ is Egyptian.",
        "entities": [{"id": "n1", "type": "NATIONALITY", "original": "Egyptian", "start": 33, "end": 41}],
    }
    optimizer = V2Optimizer()
    prepared, _, tokens = optimizer.prepare(request)
    assert "__FN_PERSON_0001__" in request["document"]
    assert tokens["n1"] == "__FN_NATIONALITY_0001__"
    assert prepared.entities[0].original == "Egyptian"


def test_budget_sweep_reports_infeasible_and_feasible_points():
    points = V2Optimizer().sweep(make_golden_fixture(), [0, 1, 2])
    assert [point["status"] for point in points] == ["FEASIBLE", "FEASIBLE", "FEASIBLE"]
    assert [point["specificity"] for point in points] == pytest.approx([1.4, 1.0, 0.8])
