from __future__ import annotations

import hashlib

from common import DATA, read_jsonl, write_jsonl


def split_for(group_id: str) -> str:
    bucket = int(hashlib.sha256(("finaira-laya-2026:" + group_id).encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def rebalance(groups: list[str]) -> dict[str, str]:
    # Ten contrast groups are small enough that hash buckets can leave a split
    # empty. Sort by the stable digest and assign 7/2/1 without separating any
    # translations, paraphrases, prompt rows, or entity decisions.
    ordered = sorted(groups, key=lambda g: hashlib.sha256(("finaira-laya-2026:" + g).encode()).hexdigest())
    mapping = {}
    train_end = max(1, round(len(ordered) * 0.70))
    validation_end = max(train_end + 1, round(len(ordered) * 0.85))
    for index, group in enumerate(ordered):
        mapping[group] = "train" if index < train_end else ("validation" if index < validation_end else "test")
    return mapping


def main() -> None:
    prompts = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    decisions = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    groups = sorted({row["split_group_id"] for row in prompts})
    mapping = rebalance(groups)
    for row in prompts:
        row["split"] = mapping[row["split_group_id"]]
    for row in decisions:
        row["split"] = mapping[row["split_group_id"]]
    write_jsonl(DATA / "generated" / "prompt_level.jsonl", prompts)
    write_jsonl(DATA / "generated" / "entity_decisions.jsonl", decisions)
    write_jsonl(DATA / "pending_review" / "prompt_level.jsonl", prompts)
    write_jsonl(DATA / "pending_review" / "entity_decisions.jsonl", decisions)
    counts = {name: sum(1 for group in groups if mapping[group] == name) for name in ["train", "validation", "test"]}
    print(f"Assigned grouped splits: {counts}")


if __name__ == "__main__":
    main()

