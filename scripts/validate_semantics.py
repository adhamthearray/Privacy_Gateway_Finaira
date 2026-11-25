from __future__ import annotations

import json
from collections import Counter, defaultdict

from common import DATA, ENTITY_TYPES, LABELS, LANGUAGES, ROOT, normalize_prompt, read_jsonl


REQUIRED_FIELDS = {
    "sample_id", "task_specification_id", "prompt_family_id", "contrast_group_id",
    "user_prompt", "task_requirements", "target_entity_type", "proposed_label",
    "approved_gold_label", "proposed_reason", "approved_reason", "task_family",
    "task_subfamily", "language", "dialect", "writing_style", "prompt_variation_type",
    "difficulty", "hard_negative_category", "generation_method", "source_provenance",
    "ambiguity_status", "semantic_validation_status", "annotation_status", "reviewer_id",
    "reviewer_notes", "split",
}


def validate() -> list[str]:
    errors: list[str] = []
    prompts = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    rows = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    if len(prompts) < 100 or len(prompts) > 200:
        errors.append(f"Pilot prompt count outside 100–200: {len(prompts)}")
    if len(rows) != len(prompts) * 10:
        errors.append("Every prompt must have exactly ten decision rows")
    by_prompt = defaultdict(list)
    normalized = defaultdict(set)
    coverage = Counter()
    for row in rows:
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            errors.append(f"{row.get('sample_id')}: missing {sorted(missing)}")
        if row["target_entity_type"] not in ENTITY_TYPES:
            errors.append(f"Unsupported type: {row['target_entity_type']}")
        if row["proposed_label"] not in LABELS:
            errors.append(f"Unsupported label: {row['proposed_label']}")
        if not row["user_prompt"].strip():
            errors.append(f"Empty prompt: {row['sample_id']}")
        if row["approved_gold_label"] is not None or row["annotation_status"] != "PENDING_REVIEW":
            errors.append(f"Synthetic row falsely approved: {row['sample_id']}")
        if row["proposed_label"] == "SEMI_RELEVANT":
            reason = row["proposed_reason"].casefold()
            if not any(term in reason for term in ["context", "enrich", "orient", "scale", "clarify"]):
                errors.append(f"Weak semi-relevant rationale: {row['sample_id']}")
        by_prompt[row["prompt_id"]].append(row)
        normalized[normalize_prompt(row["user_prompt"])].add(row["proposed_label"] + ":" + row["target_entity_type"])
        coverage[(row["target_entity_type"], row["proposed_label"], row["language_code"])] += 1
    for prompt_id, group in by_prompt.items():
        if {row["target_entity_type"] for row in group} != set(ENTITY_TYPES):
            errors.append(f"Incomplete type sweep: {prompt_id}")
        if len(group) != 10:
            errors.append(f"Wrong decision count for {prompt_id}: {len(group)}")
        if len({row["split"] for row in group}) != 1:
            errors.append(f"Prompt rows split across partitions: {prompt_id}")
    for entity in ENTITY_TYPES:
        for label in LABELS:
            for language in LANGUAGES:
                if coverage[(entity, label, language)] == 0:
                    errors.append(f"Coverage gap: {entity}/{label}/{language}")
    group_splits = defaultdict(set)
    for row in rows:
        group_splits[row["split_group_id"]].add(row["split"])
    if any(len(splits) != 1 for splits in group_splits.values()):
        errors.append("Contrast-group leakage across splits")
    ontology = json.loads((ROOT / "entity_ontology.json").read_text(encoding="utf-8"))
    if list(ontology["entities"].keys()) != ENTITY_TYPES:
        errors.append("Ontology type order/scope differs from exact ten-type contract")
    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors[:100]))
        raise SystemExit(1)
    print("Semantic and structural validation passed")


if __name__ == "__main__":
    main()

