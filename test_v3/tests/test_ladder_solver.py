import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from test_v3.ladder import normalized_loss, permitted_ladder
from test_v3.rendering import render_document
from test_v3.solver import solve_ladders


def fixture():
    return {
        "case_id": "solver-1",
        "document": "العميل يعمل كمهندس في البنك.",
        "entities": [
            {"id": "job", "entity_type": "JOB_TITLE", "original": "مهندس", "start": 13, "end": 18, "candidates": [{"candidate_id": "j0", "text": "مهندس", "level": 0}, {"candidate_id": "j1", "text": "متخصص تقنية", "level": 1}, {"candidate_id": "j2", "text": "مهني", "level": 2}]},
            {"id": "bank", "entity_type": "BANK", "original": "البنك", "start": 22, "end": 27, "candidates": [{"candidate_id": "b0", "text": "البنك", "level": 0}, {"candidate_id": "b1", "text": "مؤسسة مصرفية", "level": 1, "policy_forbidden": True}, {"candidate_id": "b2", "text": "__FN_BANK_0001__", "level": 2}]},
        ],
    }


def test_normalized_loss_and_policy_filtering():
    assert normalized_loss(0, 1) == 0
    assert normalized_loss(1, 3) == 0.5
    assert len(permitted_ladder(fixture()["entities"][1])) == 2


def test_solver_exact_cut_forces_minimum_broader_choice():
    case = fixture()
    first = solve_ladders(case)
    assert first.status == "FEASIBLE"
    assert first.selection == {"job": 0, "bank": 0}
    second = solve_ladders(case, min_levels=first.selection, cuts=[[('job', 0), ('bank', 0)]])
    assert second.status == "FEASIBLE"
    assert second.selection != first.selection
    assert second.selection["job"] >= 1 or second.selection["bank"] >= 1


def test_no_feasible_assignment_is_reported():
    case = fixture()
    result = solve_ladders(case, min_levels={"job": 2, "bank": 1}, cuts=[[('job', 2), ('bank', 1)]])
    assert result.status == "INFEASIBLE"


def test_arabic_rendering_uses_selected_candidate():
    case = fixture()
    ladders = {entity["id"]: permitted_ladder(entity) for entity in case["entities"]}
    rendered = render_document(case, {"job": 1, "bank": 0}, ladders)
    assert "متخصص تقنية" in rendered["text"]
    assert rendered["entity_spans"]["job"]["text"] == "متخصص تقنية"
