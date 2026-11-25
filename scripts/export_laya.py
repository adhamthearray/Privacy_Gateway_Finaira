from __future__ import annotations

import csv

from common import DATA, ENTITY_TYPES, QUESTION, laya_state, read_jsonl, write_jsonl


def approved_rows(rows: list[dict]) -> list[dict]:
    return [
        row for row in rows
        if row.get("annotation_status") in {"APPROVED", "ADJUDICATED"}
        and row.get("approved_gold_label")
        and row.get("ambiguity_status") != "AMBIGUOUS_PENDING_REVIEW"
    ]


def laya_record(row: dict) -> dict:
    return {
        "state": laya_state(row),
        "questions": QUESTION,
        "expected": {"entity_type_relevance": row["approved_gold_label"]},
    }


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    gold = approved_rows(rows)
    for split in ["train", "validation", "test"]:
        write_jsonl(DATA / f"{split}.jsonl", [laya_record(row) for row in gold if row["split"] == split])
    fields = ["sample_id", "prompt_id", "user_prompt", "target_entity_type", "approved_gold_label", "approved_reason", "language", "split", "reviewer_id"]
    write_csv(DATA / "all_gold_annotations.csv", gold, fields)
    prompt_matrix = {}
    for row in gold:
        prompt_matrix.setdefault(row["prompt_id"], {"prompt_id": row["prompt_id"], "user_prompt": row["user_prompt"], "language": row["language"], "split": row["split"]})
        prompt_matrix[row["prompt_id"]][row["target_entity_type"]] = row["approved_gold_label"]
    matrix_fields = ["prompt_id", "user_prompt", "language", "split", *ENTITY_TYPES]
    write_csv(DATA / "complete_prompt_label_matrix.csv", list(prompt_matrix.values()), matrix_fields)
    print(f"Exported {len(gold)} approved decisions. Unreviewed synthetic rows were excluded.")


if __name__ == "__main__":
    main()

