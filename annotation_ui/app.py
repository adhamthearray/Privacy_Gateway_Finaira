from __future__ import annotations

import argparse
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
import pandas as pd
from sklearn.metrics import cohen_kappa_score


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import DATA, ENTITY_TYPES, LABELS, read_jsonl  # noqa: E402
from annotation_store import (  # noqa: E402
    DATABASE_DESCRIPTION,
    all_annotation_rows,
    append_adjudication,
    append_review,
    initialize,
    latest_annotation_rows,
    latest_review,
)


PROMPTS = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
PROMPT_BY_ID = {row["prompt_id"]: row for row in PROMPTS}


def choices(language, family, status, entity, label, difficulty, hard_negative):
    rows = PROMPTS
    if language and language != "ALL":
        rows = [row for row in rows if row["language_code"] == language]
    if family and family != "ALL":
        rows = [row for row in rows if row["task_family"] == family]
    if status and status != "ALL":
        rows = [row for row in rows if row["annotation_status"] == status]
    if entity and entity != "ALL" and label and label != "ALL":
        rows = [row for row in rows if row["proposed_labels"].get(entity) == label]
    if difficulty and difficulty != "ALL":
        rows = [row for row in rows if row["difficulty"] == difficulty]
    if hard_negative and hard_negative != "ALL":
        rows = [row for row in rows if row["hard_negative_category"] == hard_negative]
    return gr.update(choices=[row["prompt_id"] for row in rows], value=rows[0]["prompt_id"] if rows else None)


def display(prompt_id):
    if not prompt_id or prompt_id not in PROMPT_BY_ID:
        return "", "", pd.DataFrame(), pd.DataFrame()
    row = PROMPT_BY_ID[prompt_id]
    matrix = pd.DataFrame(
        [
            {
                "entity_type": entity,
                "proposed_label": row["proposed_labels"][entity],
                "reviewer_label": row["proposed_labels"][entity],
                "proposed_reason": row["proposed_reasons"][entity],
                "approved_reason": "",
                "ambiguous": False,
            }
            for entity in ENTITY_TYPES
        ]
    )
    group = pd.DataFrame(
        [
            {"prompt_id": other["prompt_id"], "language": other["language_code"], "task": other["user_prompt"], "subfamily": other["task_subfamily"]}
            for other in PROMPTS if other["contrast_group_id"] == row["contrast_group_id"]
        ]
    )
    metadata = json.dumps({key: row[key] for key in ["language", "dialect", "task_family", "task_subfamily", "difficulty", "hard_negative_category", "task_requirements", "semantic_validation_status"]}, ensure_ascii=False, indent=2)
    return row["user_prompt"], metadata, matrix, group


def save(prompt_id, reviewer_id, edited_prompt, table, notes, action):
    if not reviewer_id.strip():
        return "Reviewer ID is required; nothing was saved."
    if not prompt_id:
        return "Select a prompt first."
    frame = pd.DataFrame(table, columns=["entity_type", "proposed_label", "reviewer_label", "proposed_reason", "approved_reason", "ambiguous"])
    if action != "REJECT_PROMPT":
        invalid = [str(value) for value in frame["reviewer_label"] if str(value) not in LABELS]
        if invalid:
            return f"Invalid labels {invalid!r}; nothing was saved."
        if set(frame["entity_type"]) != set(ENTITY_TYPES) or len(frame) != 10:
            return "The complete ten-type matrix is required; nothing was saved."
    now = datetime.now(timezone.utc).isoformat()
    records = frame.to_dict("records") if action != "REJECT_PROMPT" else []
    for record in records:
        record["reviewer_label"] = str(record["reviewer_label"])
    append_review(prompt_id, reviewer_id, action, edited_prompt, notes, now, records)
    return f"Saved append-only {action} by {reviewer_id} at {now}. Existing history was preserved."


def effective_reviewer(manual_reviewer: str, request: gr.Request | None) -> str:
    """Use the authenticated account when deployed; retain manual IDs for local mode."""
    authenticated = getattr(request, "username", None) if request else None
    return authenticated or manual_reviewer


def save_review(prompt_id, reviewer_id, edited_prompt, table, notes, request: gr.Request):
    return save(prompt_id, effective_reviewer(reviewer_id, request), edited_prompt, table, notes, "SAVE_REVIEW")


def reject_prompt(prompt_id, reviewer_id, edited_prompt, table, notes, request: gr.Request):
    return save(prompt_id, effective_reviewer(reviewer_id, request), edited_prompt, table, notes, "REJECT_PROMPT")


def load_latest_review(prompt_id, reviewer_id):
    base = display(prompt_id)[2]
    if not reviewer_id.strip():
        return base, "Enter a reviewer ID to resume that reviewer's latest saved matrix."
    saved = pd.DataFrame(latest_review(prompt_id, reviewer_id))
    if saved.empty:
        return base, "No previous review found; loaded proposed labels."
    latest = {row.entity_type: row for row in saved.itertuples()}
    for index, row in base.iterrows():
        if row["entity_type"] in latest:
            item = latest[row["entity_type"]]
            base.at[index, "reviewer_label"] = item.label
            base.at[index, "approved_reason"] = item.reason or ""
            base.at[index, "ambiguous"] = bool(item.ambiguity)
    return base, "Loaded the latest append-only review snapshot."


def resume_review(prompt_id, reviewer_id, request: gr.Request):
    return load_latest_review(prompt_id, effective_reviewer(reviewer_id, request))


def disagreements():
    frame = pd.DataFrame(latest_annotation_rows())
    if frame.empty:
        return pd.DataFrame(columns=["prompt_id", "entity_type", "reviewers", "labels", "has_ambiguity"])
    records = []
    for (prompt_id, entity), group in frame.groupby(["prompt_id", "entity_type"]):
        if group["reviewer_id"].nunique() >= 2 and (group["label"].nunique() > 1 or group["ambiguity"].max()):
            records.append({
                "prompt_id": prompt_id,
                "entity_type": entity,
                "reviewers": ", ".join(group["reviewer_id"].astype(str)),
                "labels": ", ".join(group["label"].astype(str)),
                "has_ambiguity": bool(group["ambiguity"].max()),
            })
    return pd.DataFrame(records)


def adjudicate(prompt_id, entity_type, adjudicator_id, label, reason):
    if not adjudicator_id.strip() or entity_type not in ENTITY_TYPES or label not in LABELS:
        return "Adjudicator ID, valid entity type, and valid label are required."
    now = datetime.now(timezone.utc).isoformat()
    append_adjudication(prompt_id, entity_type, adjudicator_id, label, reason, now)
    return f"Saved append-only adjudication at {now}. Run scripts/sync_annotations.py to materialize approved gold."


def save_adjudication(prompt_id, entity_type, adjudicator_id, label, reason, request: gr.Request):
    return adjudicate(prompt_id, entity_type, effective_reviewer(adjudicator_id, request), label, reason)


def signed_in_user(request: gr.Request):
    username = getattr(request, "username", None) if request else None
    if username:
        return f"Signed in as **{username}**. Saved reviews are attributed to this account automatically.", username
    return "Local mode: enter a stable reviewer ID before saving.", ""


def export_review_csv():
    output = ROOT / "reports" / "annotations_export.csv"
    frame = pd.DataFrame(all_annotation_rows())
    frame.to_csv(output, index=False, encoding="utf-8-sig")
    return f"Exported {len(frame)} annotation history rows.", str(output)


def authentication():
    """Build Gradio basic auth from a JSON secret; never store passwords in source."""
    raw = os.environ.get("FINAIRA_AUTH_USERS", "").strip()
    if not raw:
        return None
    try:
        users = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("FINAIRA_AUTH_USERS must be a JSON object of username/password pairs") from exc
    if not isinstance(users, dict) or not users or not all(isinstance(key, str) and isinstance(value, str) for key, value in users.items()):
        raise RuntimeError("FINAIRA_AUTH_USERS must be a non-empty JSON object of username/password pairs")

    def verify(username: str, password: str) -> bool:
        stored = users.get(username)
        return stored is not None and hmac.compare_digest(stored, password)

    return verify


def agreement():
    frame = pd.DataFrame(all_annotation_rows())
    if frame.empty or frame["reviewer_id"].nunique() < 2:
        return "Agreement is pending: at least two independent reviewers must annotate overlapping items."
    overlap = frame.groupby(["prompt_id", "entity_type"]).filter(lambda part: part["reviewer_id"].nunique() >= 2)
    if overlap.empty:
        return "Agreement is pending: reviewers have no overlapping judgments."
    per_item = overlap.groupby(["prompt_id", "entity_type"])["label"].agg(lambda labels: len(set(labels)) == 1)
    reviewers = sorted(overlap["reviewer_id"].unique())
    kappas = []
    for index, left in enumerate(reviewers):
        for right in reviewers[index + 1 :]:
            left_rows = overlap[overlap["reviewer_id"] == left].set_index(["prompt_id", "entity_type"])
            right_rows = overlap[overlap["reviewer_id"] == right].set_index(["prompt_id", "entity_type"])
            shared = left_rows.index.intersection(right_rows.index)
            if len(shared) >= 2:
                kappas.append(cohen_kappa_score(left_rows.loc[shared, "label"], right_rows.loc[shared, "label"], labels=LABELS))
    kappa_text = f" Mean pairwise Cohen's κ: {sum(kappas) / len(kappas):.3f}." if kappas else " Cohen's κ needs at least two shared items per reviewer pair."
    return f"Raw agreement: {per_item.mean():.1%} ({per_item.sum()}/{len(per_item)}).{kappa_text}"


def build_app():
    initialize()
    with gr.Blocks(title="Finaira Laya relevance annotation") as demo:
        gr.Markdown("# Finaira Laya relevance annotation\nReview prompt-conditioned entity-type relevance. Proposed labels are never gold until human approval/adjudication.")
        signed_in = gr.Markdown()
        with gr.Row():
            language = gr.Dropdown(["ALL", "en", "ar_msa", "ar_egy", "ar_en_mixed"], value="ALL", label="Language")
            family = gr.Dropdown(["ALL", *sorted({row["task_family"] for row in PROMPTS})], value="ALL", label="Task family")
            status = gr.Dropdown(["ALL", "PENDING_REVIEW"], value="PENDING_REVIEW", label="Status")
            selector = gr.Dropdown([row["prompt_id"] for row in PROMPTS], value=PROMPTS[0]["prompt_id"] if PROMPTS else None, label="Prompt ID")
        with gr.Row():
            entity_filter = gr.Dropdown(["ALL", *ENTITY_TYPES], value="ALL", label="Entity type")
            label_filter = gr.Dropdown(["ALL", *LABELS], value="ALL", label="Proposed label")
            difficulty = gr.Dropdown(["ALL", "standard", "medium", "hard"], value="ALL", label="Difficulty")
            hard_negative = gr.Dropdown(["ALL", *sorted({row["hard_negative_category"] for row in PROMPTS})], value="ALL", label="Hard-negative category")
        prompt = gr.Textbox(label="Prompt wording (editable)", lines=4)
        metadata = gr.Code(label="Specification metadata", language="json")
        matrix = gr.Dataframe(headers=["entity_type", "proposed_label", "reviewer_label", "proposed_reason", "approved_reason", "ambiguous"], datatype=["str", "str", "str", "str", "str", "bool"], interactive=True, label="Complete ten-type matrix")
        gr.Markdown("## Contrast group")
        contrast = gr.Dataframe(interactive=False)
        with gr.Row():
            reviewer = gr.Textbox(label="Reviewer ID")
            notes = gr.Textbox(label="Reviewer notes")
        with gr.Row():
            approve = gr.Button("Save independent review", variant="primary")
            reject = gr.Button("Reject prompt")
            resume = gr.Button("Resume my latest review")
            refresh_agreement = gr.Button("Calculate agreement")
            export_csv = gr.Button("Export review CSV")
        result = gr.Textbox(label="Result", interactive=False)
        download = gr.File(label="Download annotation history", interactive=False)
        selector.change(display, selector, [prompt, metadata, matrix, contrast])
        filter_inputs = [language, family, status, entity_filter, label_filter, difficulty, hard_negative]
        for control in filter_inputs:
            control.change(choices, filter_inputs, selector)
        approve.click(save_review, [selector, reviewer, prompt, matrix, notes], result)
        reject.click(reject_prompt, [selector, reviewer, prompt, matrix, notes], result)
        resume.click(resume_review, [selector, reviewer], [matrix, result])
        refresh_agreement.click(agreement, outputs=result)
        export_csv.click(export_review_csv, outputs=[result, download])
        gr.Markdown("## Disagreement review and adjudication")
        disagreement_table = gr.Dataframe(interactive=False)
        refresh_disagreements = gr.Button("Refresh disagreements")
        with gr.Row():
            adj_prompt = gr.Textbox(label="Prompt ID")
            adj_entity = gr.Dropdown(ENTITY_TYPES, label="Entity type")
            adj_reviewer = gr.Textbox(label="Adjudicator ID")
            adj_label = gr.Dropdown(LABELS, label="Final label")
        adj_reason = gr.Textbox(label="Adjudication reason")
        adj_button = gr.Button("Save adjudication")
        refresh_disagreements.click(disagreements, outputs=disagreement_table)
        adj_button.click(save_adjudication, [adj_prompt, adj_entity, adj_reviewer, adj_label, adj_reason], result)
        demo.load(display, selector, [prompt, metadata, matrix, contrast])
        demo.load(signed_in_user, outputs=[signed_in, reviewer])
    return demo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Build the UI and database without opening a server.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "7860")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    demo = build_app()
    if args.check:
        print(f"Annotation UI built successfully with {len(PROMPTS)} prompts; database: {DATABASE_DESCRIPTION}")
        return
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        inbrowser=not args.no_browser,
        auth=authentication(),
        auth_message="Sign in with the reviewer account provided by the study administrator.",
    )


if __name__ == "__main__":
    main()

