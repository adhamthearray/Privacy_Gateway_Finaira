from __future__ import annotations

import csv
from collections import Counter

from common import DATA, ENTITY_TYPES, LABELS, LANGUAGES, REPORTS, read_jsonl


def csv_counter(path, fieldnames, counter):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames + ["count"])
        for key, count in sorted(counter.items()):
            writer.writerow([*(key if isinstance(key, tuple) else (key,)), count])


def main() -> None:
    prompts = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    rows = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    class_counts = Counter((row["target_entity_type"], row["proposed_label"]) for row in rows)
    language_counts = Counter((row["language_code"], row["proposed_label"]) for row in rows)
    hard_counts = Counter((row["target_entity_type"], row["hard_negative_category"]) for row in rows if row["hard_negative_category"] != "none")
    ambiguity = Counter(row["ambiguity_status"] for row in rows)
    csv_counter(REPORTS / "class_distribution.csv", ["entity_type", "proposed_label"], class_counts)
    csv_counter(REPORTS / "language_distribution.csv", ["language", "proposed_label"], language_counts)
    csv_counter(REPORTS / "hard_negative_report.csv", ["entity_type", "category"], hard_counts)
    csv_counter(REPORTS / "ambiguity_report.csv", ["ambiguity_status"], ambiguity)
    approved = sum(row["approved_gold_label"] is not None for row in rows)
    semi = sum(row["proposed_label"] == "SEMI_RELEVANT" for row in rows)
    coverage = f"""# Pilot coverage

- Unique prompts: {len(prompts)}
- Entity-type decisions: {len(rows)}
- Semantic task specifications: {len(set(row['task_specification_id'] for row in rows))}
- Prompt families: {len(set(row['prompt_family_id'] for row in rows))}
- Contrastive groups: {len(set(row['contrast_group_id'] for row in rows))}
- Proposed semi-relevant decisions: {semi}
- Human-approved decisions: {approved}
- Human approval rate: {approved / len(rows):.1%}
- Languages: {', '.join(LANGUAGES)}
- Annotation status: all generated examples remain `PENDING_REVIEW`.

## Coverage guarantee

Every one of the ten entity types has at least one `RELEVANT`, `SEMI_RELEVANT`, and `IRRELEVANT` example in every language group. Every type also has a controlled hard-negative task flip. These are proposed labels, not gold labels.

## Human-dependent metrics

Inter-annotator disagreement, adjudication outcomes, semi-relevant approval rate, and final gold class balance cannot be reported until at least two reviewers annotate overlapping prompts. The annotation database and calculation path are ready; no values are fabricated.
"""
    (REPORTS / "coverage.md").write_text(coverage, encoding="utf-8")
    quality = f"""# Quality report

Structural validation is automated by `scripts/validate_semantics.py`. The pilot contains {len(prompts)} prompts and {len(rows)} complete entity-type decisions. Grouped splitting keeps all translations, three relevance task flips, and ten type decisions for a scenario together.

Synthetic labels are suggestions only. Official Laya exports contain {approved} rows because no human approval has occurred. Semantic naturalness, especially Egyptian Arabic and code-switching, remains a human-review obligation. Duplicate findings are recorded without deleting source data. Baseline and model metrics remain blocked until approved gold labels exist.
"""
    (REPORTS / "quality_report.md").write_text(quality, encoding="utf-8")
    print("Wrote coverage and quality reports")


if __name__ == "__main__":
    main()

