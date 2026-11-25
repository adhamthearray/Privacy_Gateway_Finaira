from __future__ import annotations

from common import DATA, ENTITY_TYPES, ensure_dirs, read_jsonl, stable_id, write_jsonl
from catalog import LANGUAGE_META


def main() -> None:
    ensure_dirs()
    specs = read_jsonl(DATA / "task_specs" / "pilot_task_specs.jsonl")
    prompt_rows, decisions = [], []
    for spec in specs:
        target = spec["target_entity_type"]
        mode = spec["contrast_mode"]
        contrast_group = spec.get("contrast_group_id", f"CG_{target}")
        prompt_family = f"PF_{target}_{mode.upper()}"
        for lang_key, prompt in spec["prompts"].items():
            language, dialect, style = LANGUAGE_META[lang_key]
            prompt_id = stable_id("PROMPT", spec["specification_id"], lang_key, prompt)
            split_group = contrast_group
            prompt_row = {
                "prompt_id": prompt_id,
                "task_specification_id": spec["specification_id"],
                "prompt_family_id": prompt_family,
                "contrast_group_id": contrast_group,
                "split_group_id": split_group,
                "user_prompt": prompt,
                "task_requirements": spec["task_requirements"],
                "proposed_labels": spec["proposed_labels_for_all_10_types"],
                "approved_labels": {},
                "proposed_reasons": spec["proposed_reasons_for_all_10_types"],
                "approved_reasons": {},
                "task_family": spec["task_family"],
                "task_subfamily": spec["task_subfamily"],
                "language": language,
                "language_code": lang_key,
                "dialect": dialect,
                "writing_style": style,
                "prompt_variation_type": {
                    "relevant": "direct_or_implicit_requirement",
                    "semi": "authorized_optional_context",
                    "irrelevant": "explicit_exclusion_hard_negative",
                }.get(mode, "compound_or_conditional_task"),
                "difficulty": "hard" if mode in {"irrelevant", "composite"} else ("medium" if mode == "semi" else "standard"),
                "hard_negative_category": f"{target.lower()}_vs_{spec['required_information'][0].lower()}" if mode == "irrelevant" else "none",
                "generation_method": "human-designed specification + deterministic multilingual rendering",
                "source_provenance": "project-authored synthetic prompt; no private or customer data",
                "ambiguity_status": "NOT_FLAGGED",
                "semantic_validation_status": "RULE_VALIDATED_PENDING_HUMAN",
                "annotation_status": "PENDING_REVIEW",
                "reviewer_id": None,
                "reviewer_notes": None,
                "split": None,
            }
            prompt_rows.append(prompt_row)
            for entity in ENTITY_TYPES:
                decisions.append(
                    {
                        "sample_id": stable_id("SAMPLE", prompt_id, entity),
                        "task_specification_id": spec["specification_id"],
                        "prompt_id": prompt_id,
                        "prompt_family_id": prompt_family,
                        "contrast_group_id": contrast_group,
                        "split_group_id": split_group,
                        "user_prompt": prompt,
                        "task_requirements": spec["task_requirements"],
                        "target_entity_type": entity,
                        "proposed_label": spec["proposed_labels_for_all_10_types"][entity],
                        "approved_gold_label": None,
                        "proposed_reason": spec["proposed_reasons_for_all_10_types"][entity],
                        "approved_reason": None,
                        "task_family": spec["task_family"],
                        "task_subfamily": spec["task_subfamily"],
                        "language": language,
                        "language_code": lang_key,
                        "dialect": dialect,
                        "writing_style": style,
                        "prompt_variation_type": prompt_row["prompt_variation_type"],
                        "difficulty": prompt_row["difficulty"],
                        "hard_negative_category": prompt_row["hard_negative_category"],
                        "generation_method": prompt_row["generation_method"],
                        "source_provenance": prompt_row["source_provenance"],
                        "ambiguity_status": "NOT_FLAGGED",
                        "semantic_validation_status": "RULE_VALIDATED_PENDING_HUMAN",
                        "annotation_status": "PENDING_REVIEW",
                        "reviewer_id": None,
                        "reviewer_notes": None,
                        "split": None,
                    }
                )
    write_jsonl(DATA / "generated" / "prompt_level.jsonl", prompt_rows)
    write_jsonl(DATA / "generated" / "entity_decisions.jsonl", decisions)
    write_jsonl(DATA / "pending_review" / "prompt_level.jsonl", prompt_rows)
    write_jsonl(DATA / "pending_review" / "entity_decisions.jsonl", decisions)
    print(f"Wrote {len(prompt_rows)} prompts and {len(decisions)} entity decisions")


if __name__ == "__main__":
    main()

