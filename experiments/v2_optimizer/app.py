"""Standalone Finaira V2 comparison playground."""

from __future__ import annotations

import json
import os
import tempfile
import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finaira.v2 import EvaluationTargets, V2Optimizer, build_real_examples, export_csv  # noqa: E402


DB_PATH = ROOT / "data" / "processed" / "finaira_generalization.db"
EXAMPLES = build_real_examples(DB_PATH)
OPTIMIZER = V2Optimizer(DB_PATH)
TASKS = ["professional_summary", "customer_demographic_summary", "age_eligibility", "nationality_country_eligibility", "financial_field_extraction", "financial_transaction_summary"]
CSS = ".rtl textarea { direction: rtl; text-align: right; } .note { padding: 10px; border: 1px solid #d97706; border-radius: 8px; }"


def _load_example(name: str):
    item = EXAMPLES.get(name, {})
    return item.get("case_id", "case-ui"), item.get("task", TASKS[0]), item.get("document", ""), json.dumps(item.get("entities", []), ensure_ascii=False, indent=2)


def _request(case_id: str, task: str, document: str, entities_json: str) -> dict:
    try:
        entities = json.loads(entities_json or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"ENTITIES_JSON_INVALID:{exc.msg}") from exc
    if not isinstance(entities, list) or not entities:
        raise ValueError("ENTITIES_MUST_BE_NONEMPTY_ARRAY")
    return {"case_id": case_id or "case-ui", "task": task, "document": document, "entities": entities}


def _inventory(request: dict) -> list[list]:
    prepared, _, _ = OPTIMIZER.prepare(request)
    rows = []
    for entity in prepared.entities:
        for candidate in entity.candidates:
            rows.append([entity.entity_id, entity.entity_type, candidate.text, candidate.utility_loss, candidate.specificity, candidate.transformation, candidate.metadata.get("method"), candidate.terminal_pseudonym, candidate.metadata.get("candidate_id")])
    return rows


def _comparison_rows(comparison: dict) -> list[list]:
    rows = []
    for method in ("baseline", "greedy", "v2"):
        metrics = comparison.get(method, {}).get("metrics", {})
        rows.append([method, comparison.get(method, {}).get("status"), metrics.get("total_utility_loss"), metrics.get("total_specificity"), metrics.get("normalized_specificity"), metrics.get("detailed_qi_count"), metrics.get("pseudonymized_entity_count"), metrics.get("mandatory_fact_satisfaction"), metrics.get("policy_compliance"), metrics.get("runtime_ms"), metrics.get("solver_status")])
    return rows


def run_comparison(case_id, task, document, entities_json, max_utility_loss, detailed_threshold, detailed_limit):
    try:
        request = _request(case_id, task, document, entities_json)
        comparison = OPTIMIZER.compare(request, max_utility_loss=float(max_utility_loss), detailed_qi_threshold=float(detailed_threshold), detailed_qi_limit=None if detailed_limit in (None, "") else int(detailed_limit), targets=EvaluationTargets())
        comparison["candidate_inventory"] = _inventory(request)
        comparison["input_contract"] = {"policy_generalization_required": True, "database_lookup": "exact/direct only", "raw_original_selectable": False}
        temp = Path(tempfile.mkstemp(prefix="finaira_v2_", suffix=".csv")[1])
        export_csv(comparison, temp)
        status = f"V1={comparison['baseline']['status']} | Greedy={comparison['greedy']['status']} | V2={comparison['v2']['status']} | {comparison['evaluation']['status']}"
        return status, _comparison_rows(comparison), comparison["baseline"].get("transformed_document"), comparison["greedy"].get("transformed_document"), comparison["v2"].get("transformed_document"), _inventory(request), comparison, str(temp)
    except Exception as exc:
        error = {"error": f"{type(exc).__name__}:{exc}"}
        return f"ERROR: {error['error']}", [], "", "", "", [], error, None


def run_sweep(case_id, task, document, entities_json, budgets_text, detailed_threshold, detailed_limit):
    try:
        request = _request(case_id, task, document, entities_json)
        budgets = [float(value.strip()) for value in str(budgets_text).split(",") if value.strip()]
        return OPTIMIZER.sweep(request, budgets, detailed_qi_threshold=float(detailed_threshold), detailed_qi_limit=None if detailed_limit in (None, "") else int(detailed_limit))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}:{exc}"}


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Finaira V2 Optimizer Playground") as demo:
        gr.Markdown("# Finaira V2 Optimizer Playground\nTask-constrained, document-level structural information minimization. The database examples below are verified exact/direct matches; no substring-only example is loaded.")
        gr.Markdown("<div class='note'><b>Important:</b> V2 does not call an LLM. Its specificity metric is structural, not re-identification risk. If no ground-truth evaluator is supplied, the dashboard reports optimization comparison only.</div>")
        with gr.Row():
            scenario = gr.Dropdown(choices=list(EXAMPLES), value=list(EXAMPLES)[0], label="Verified database scenario")
            load = gr.Button("Load exact-match scenario")
        with gr.Row():
            case_id = gr.Textbox(label="Case ID")
            task = gr.Dropdown(choices=TASKS, value=TASKS[0], label="Task profile")
        document = gr.Textbox(label="Semi-sanitized document", lines=8, elem_classes=["rtl"])
        entities = gr.Textbox(label="Upstream generalizable entities JSON (original values and offsets)", lines=12, elem_classes=["rtl"])
        with gr.Row():
            budget = gr.Number(value=1, label="Maximum modeled utility loss")
            threshold = gr.Number(value=0.8, label="Detailed-QI specificity threshold")
            limit = gr.Number(value=None, label="Detailed-QI limit (blank = unlimited)", precision=0)
        with gr.Row():
            run = gr.Button("Run V1 / Greedy / V2", variant="primary")
            sweep = gr.Button("Sweep utility budgets")
        status = gr.Markdown()
        comparison_table = gr.Dataframe(headers=["Method", "Status", "Utility loss", "Specificity", "Normalized specificity", "Detailed QIs", "Pseudonyms", "Mandatory facts", "Policy", "Runtime ms", "Solver status"], interactive=False)
        with gr.Row():
            baseline_doc = gr.Textbox(label="Independent V1 transformed document", lines=8, interactive=False, elem_classes=["rtl"])
            greedy_doc = gr.Textbox(label="Greedy transformed document", lines=8, interactive=False, elem_classes=["rtl"])
            v2_doc = gr.Textbox(label="V2 MILP transformed document", lines=8, interactive=False, elem_classes=["rtl"])
        gr.Markdown("### Candidate inventory and decision trace")
        candidate_table = gr.Dataframe(headers=["Entity", "Type", "Candidate", "Utility loss", "Specificity", "Transformation", "Scoring method", "Terminal pseudonym", "Candidate ID"], interactive=False)
        result_json = gr.JSON(label="Full comparison result")
        sweep_json = gr.JSON(label="Utility–disclosure frontier")
        csv_file = gr.File(label="Candidate comparison CSV")
        load.click(_load_example, inputs=scenario, outputs=[case_id, task, document, entities])
        run.click(run_comparison, inputs=[case_id, task, document, entities, budget, threshold, limit], outputs=[status, comparison_table, baseline_doc, greedy_doc, v2_doc, candidate_table, result_json, csv_file])
        sweep.click(run_sweep, inputs=[case_id, task, document, entities, gr.Textbox(value="0,0.5,1,2,3,5", label="Sweep budgets"), threshold, limit], outputs=sweep_json)
    return demo


def main() -> None:
    port = int(os.environ.get("FINAIRA_V2_PORT", "7862"))
    build_app().launch(server_name="127.0.0.1", server_port=port, share=False, show_error=True, css=CSS)


if __name__ == "__main__":
    main()
