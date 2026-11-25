from __future__ import annotations

from collections import defaultdict

from annotation_store import DATABASE_DESCRIPTION, initialize, latest_adjudication_rows, latest_annotation_rows
from common import DATA, read_jsonl, write_jsonl


def main() -> None:
    initialize()
    annotations = latest_annotation_rows()
    adjudications = latest_adjudication_rows()
    by_item = defaultdict(list)
    for record in annotations:
        by_item[(record["prompt_id"], record["entity_type"])].append(record)
    final = {}
    for record in adjudications:
        final[(record["prompt_id"], record["entity_type"])] = (
            record["label"], record["reason"], record["adjudicator_id"], "ADJUDICATED"
        )
    for key, group in by_item.items():
        if key in final or len({row["reviewer_id"] for row in group}) < 2 or any(row["ambiguity"] for row in group):
            continue
        labels = {row["label"] for row in group}
        if len(labels) == 1:
            label = next(iter(labels))
            reasons = [row["reason"] for row in group if row["reason"]]
            final[key] = (label, " | ".join(reasons), ",".join(sorted({row["reviewer_id"] for row in group})), "APPROVED")
    decisions = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    for row in decisions:
        item = final.get((row["prompt_id"], row["target_entity_type"]))
        if item:
            row["approved_gold_label"], row["approved_reason"], row["reviewer_id"], row["annotation_status"] = item
    write_jsonl(DATA / "generated" / "entity_decisions.jsonl", decisions)
    write_jsonl(DATA / "approved" / "entity_decisions.jsonl", [row for row in decisions if row["annotation_status"] in {"APPROVED", "ADJUDICATED"}])
    write_jsonl(DATA / "pending_review" / "entity_decisions.jsonl", [row for row in decisions if row["annotation_status"] == "PENDING_REVIEW"])
    prompt_rows = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    decisions_by_prompt = defaultdict(list)
    for row in decisions:
        decisions_by_prompt[row["prompt_id"]].append(row)
    for prompt in prompt_rows:
        group = decisions_by_prompt[prompt["prompt_id"]]
        prompt["approved_labels"] = {row["target_entity_type"]: row["approved_gold_label"] for row in group if row["approved_gold_label"]}
        prompt["approved_reasons"] = {row["target_entity_type"]: row["approved_reason"] for row in group if row["approved_reason"]}
        if len(prompt["approved_labels"]) == 10:
            prompt["annotation_status"] = "APPROVED"
    write_jsonl(DATA / "generated" / "prompt_level.jsonl", prompt_rows)
    write_jsonl(DATA / "approved" / "prompt_level.jsonl", [row for row in prompt_rows if row["annotation_status"] == "APPROVED"])
    write_jsonl(DATA / "pending_review" / "prompt_level.jsonl", [row for row in prompt_rows if row["annotation_status"] == "PENDING_REVIEW"])
    print(f"Materialized {len(final)} consensus/adjudicated gold decisions from {DATABASE_DESCRIPTION}; annotation history remains append-only.")


if __name__ == "__main__":
    main()
