"""Standalone Gradio playground for local multi-token completion experiments."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import gradio as gr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finaira_generalization import GeneralizationDB  # noqa: E402

from examples import EXAMPLES  # noqa: E402
from model import ENTITY_TYPES, MODEL_CHOICES, MaskedLMCompletion, replace_occurrence  # noqa: E402


DB_PATH = ROOT / "data/processed/finaira_generalization.db"
GENERATOR = MaskedLMCompletion()
APP_CSS = """
.rtl textarea { direction: rtl; text-align: right; }
.warning { border: 1px solid #d97706; padding: 10px; border-radius: 8px; }
"""


def _language_for_text(text: str) -> str:
    return "ar" if any("\u0600" <= char <= "\u06ff" for char in text) else "en"


def _load_example(name: str):
    item = EXAMPLES.get(name, {})
    return item.get("text", ""), item.get("span", ""), item.get("entity_type", "OTHER")


def _parse_specs(
    document: str,
    span: str,
    entity_type: str,
    occurrence: float | int,
    multi_mode: bool,
    multi_spec: str,
) -> list[dict[str, Any]]:
    if not multi_mode:
        return [{
            "entity_id": "E0001",
            "span": span,
            "entity_type": entity_type,
            "occurrence": int(occurrence or 1),
        }]
    try:
        parsed = json.loads(multi_spec or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"MULTI_ENTITY_JSON_INVALID: {exc.msg}") from exc
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("MULTI_ENTITY_SPEC_MUST_BE_NONEMPTY_ARRAY")
    specs = []
    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"MULTI_ENTITY_ITEM_MUST_BE_OBJECT:{index}")
        specs.append({
            "entity_id": str(item.get("entity_id") or f"E{index:04d}"),
            "span": str(item.get("span") or ""),
            "entity_type": str(item.get("entity_type") or "OTHER").upper(),
            "occurrence": int(item.get("occurrence") or 1),
        })
    return specs


def _deterministic_candidates(span: str, entity_type: str, language: str) -> list[dict[str, Any]]:
    if entity_type == "OTHER":
        return []
    try:
        result = GeneralizationDB(DB_PATH).get_candidates(
            entity_type,
            span,
            output_language=language,
            include_review_candidates=True,
            input_language=language,
        )
    except Exception as exc:  # The experiment must remain usable without DB comparison.
        return [{"comparison_error": f"{type(exc).__name__}: {exc}"}]
    fields = (
        "candidate_id", "level_code", "representation", "label_en", "label_ar",
        "verification_status", "available", "is_exact", "is_suppression",
        "source", "provenance",
    )
    return [{key: candidate.get(key) for key in fields} for candidate in result.get("candidates", [])]


def _export_json(payload: dict[str, Any]) -> str:
    handle = tempfile.NamedTemporaryFile(prefix="finaira_mtc_", suffix=".json", delete=False, mode="w", encoding="utf-8")
    with handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return handle.name


def generate(
    document: str,
    span: str,
    entity_type: str,
    occurrence: float | int,
    language: str,
    model_name: str,
    num_candidates: float | int,
    masking_mode: str,
    fixed_length: float | int,
    device: str,
    multi_mode: bool,
    multi_spec: str,
    compare_db: bool,
):
    try:
        if not document or not document.strip():
            raise ValueError("DOCUMENT_REQUIRED")
        specs = _parse_specs(document, span, entity_type, occurrence, multi_mode, multi_spec)
        resolved_language = language if language != "auto" else _language_for_text(document)
        results = []
        combined_text = document
        for spec in specs:
            if spec["entity_type"] not in ENTITY_TYPES:
                raise ValueError(f"UNSUPPORTED_ENTITY_TYPE:{spec['entity_type']}")
            result = GENERATOR.generate(
                document,
                spec["span"],
                spec["entity_type"],
                occurrence=spec["occurrence"],
                model_name=model_name,
                language=resolved_language,
                num_candidates=int(num_candidates),
                masking_mode=masking_mode,
                fixed_length=int(fixed_length),
                device=device,
            )
            result["entity_id"] = spec["entity_id"]
            if compare_db:
                result["finaira_deterministic_candidates"] = _deterministic_candidates(
                    spec["span"], spec["entity_type"], resolved_language
                )
            results.append(result)
            top = result["candidates"][0]["replacement"]
            combined_text = replace_occurrence(combined_text, spec["span"], top, spec["occurrence"])

        output = {
            "mode": "MULTI_ENTITY" if multi_mode else "SINGLE_ENTITY",
            "method": GENERATOR.method_name,
            "official_ss_mtc": GENERATOR.official_ss_mtc,
            "results": results,
            "combined_transformed_text": combined_text,
            "warning": "Generated replacements are experimental proposals, not automatically privacy-safe generalizations.",
        }
        rows = []
        for result in results:
            for candidate in result["candidates"]:
                rows.append([
                    result["entity_id"],
                    candidate["rank"],
                    candidate["replacement"],
                    candidate["log_score"],
                    candidate["reconstructed_text"],
                    candidate["entity_type_consistency"],
                    candidate["broader_than_original"],
                    candidate["privacy_safety"],
                    " | ".join(candidate["warnings"]),
                ])
        status = f"Generated {sum(len(item['candidates']) for item in results)} candidate(s) locally. Method: `{GENERATOR.method_name}`. SS-MTC: `no`."
        return status, document, combined_text, rows, output, _export_json(output)
    except Exception as exc:
        error = {"error": f"{type(exc).__name__}: {exc}"}
        return f"**Error:** `{error['error']}`", document or "", "", [], error, None


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="Finaira Multi-Token Completion Playground",
    ) as demo:
        gr.Markdown(
            "# Finaira Multi-Token Completion Playground\n"
            "Experimental local inference only. This playground proposes text replacements; it does not authorize privacy-safe transformations."
        )
        with gr.Row():
            with gr.Column(scale=2):
                document = gr.Textbox(
                    label="Document text",
                    lines=12,
                    elem_classes=["rtl"],
                    placeholder="Paste English or Arabic financial text here...",
                )
                with gr.Row():
                    example = gr.Dropdown(choices=list(EXAMPLES), value=list(EXAMPLES)[0], label="Sample")
                    load_sample = gr.Button("Load sample")
                span = gr.Textbox(label="Exact entity span", placeholder="e.g. National Bank of Egypt", elem_classes=["rtl"])
                entity_type = gr.Dropdown(choices=ENTITY_TYPES, value="BANK", label="Entity type")
                occurrence = gr.Number(value=1, minimum=1, precision=0, label="Occurrence to replace (1-based)")
                multi_mode = gr.Checkbox(label="Multi-entity mode", value=False)
                multi_spec = gr.Textbox(
                    label="Multi-entity JSON array",
                    lines=5,
                    value='[{"entity_id":"E0001","span":"John Doe","entity_type":"PERSON_NAME","occurrence":1}]',
                    visible=False,
                )
            with gr.Column(scale=1):
                gr.Markdown("### Model settings")
                model_name = gr.Dropdown(
                    choices=MODEL_CHOICES,
                    value=MODEL_CHOICES[0],
                    allow_custom_value=True,
                    label="Model/checkpoint",
                )
                language = gr.Radio(["auto", "en", "ar"], value="auto", label="Language mode")
                num_candidates = gr.Slider(1, 10, value=5, step=1, label="Replacement candidates")
                masking_mode = gr.Radio(["adaptive", "fixed"], value="adaptive", label="Masking mode")
                fixed_length = gr.Slider(1, 10, value=3, step=1, label="Fixed mask length")
                device = gr.Radio(["auto", "cpu", "cuda"], value="auto", label="Inference device")
                compare_db = gr.Checkbox(label="Compare Finaira deterministic candidates (read-only)", value=True)
                generate_button = gr.Button("Generate Generalizations", variant="primary")
        status = gr.Markdown()
        gr.Markdown(
            "<div class='warning'><b>Safety:</b> model likelihood is not privacy or utility confidence. "
            "Entity consistency, breadth, and privacy safety are intentionally marked as unverified unless a separate validator confirms them.</div>"
        )
        with gr.Row():
            original_output = gr.Textbox(label="Original document", lines=10, interactive=False, elem_classes=["rtl"])
            transformed_output = gr.Textbox(label="Top-1 reconstructed document", lines=10, interactive=False, elem_classes=["rtl"])
        results_table = gr.Dataframe(
            headers=["Entity", "Rank", "Replacement", "Log score", "Reconstructed text", "Type consistency", "Broader", "Privacy safety", "Warnings"],
            datatype=["str", "number", "str", "number", "str", "str", "str", "str", "str"],
            label="Generated candidates",
            interactive=False,
            wrap=True,
        )
        json_output = gr.JSON(label="Full experiment result")
        download = gr.File(label="Export JSON")

        load_sample.click(_load_example, inputs=example, outputs=[document, span, entity_type])
        multi_mode.change(lambda enabled: gr.update(visible=enabled), inputs=multi_mode, outputs=multi_spec)
        generate_button.click(
            generate,
            inputs=[document, span, entity_type, occurrence, language, model_name, num_candidates, masking_mode, fixed_length, device, multi_mode, multi_spec, compare_db],
            outputs=[status, original_output, transformed_output, results_table, json_output, download],
        )
    return demo


def main() -> None:
    port = int(os.environ.get("FINAIRA_MTC_PORT", "7860"))
    build_app().launch(server_name="127.0.0.1", server_port=port, share=False, show_error=True, css=APP_CSS)


if __name__ == "__main__":
    main()

