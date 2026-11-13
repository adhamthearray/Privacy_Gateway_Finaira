"""Export unique NER values for the supported generalization entity types."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ENTITY_TYPES = ("BANK", "COUNTRY", "NATIONALITY", "CORPORATION", "GOVERNMENT_ENTITY", "JOB_TITLE", "OCCUPATION", "AGE", "DATE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/ner_v1_generalization"))
    args = parser.parse_args()
    values: dict[str, Counter[str]] = defaultdict(Counter)
    files: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in sorted(args.dataset.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                for span in row.get("spans", []):
                    entity_type = span["label"]
                    if entity_type in ENTITY_TYPES:
                        value = span["text"]
                        values[entity_type][value] += 1
                        files[(entity_type, value)].add(path.name)
    args.output.mkdir(parents=True, exist_ok=True)
    combined = []
    for entity_type in ENTITY_TYPES:
        rows = [{"entity_type": entity_type, "value": value, "span_count": count, "source_files": ";".join(sorted(files[(entity_type, value)]))} for value, count in sorted(values[entity_type].items(), key=lambda item: (-item[1], item[0]))]
        combined.extend(rows)
        path = args.output / f"{entity_type.lower()}_unique_values.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["entity_type", "value", "span_count", "source_files"])
            writer.writeheader()
            writer.writerows(rows)
    combined_path = args.output / "all_generalization_unique_values.csv"
    with combined_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["entity_type", "value", "span_count", "source_files"])
        writer.writeheader()
        writer.writerows(combined)
    print(json.dumps({"output_dir": str(args.output), "entity_counts": {entity_type: len(values[entity_type]) for entity_type in ENTITY_TYPES}, "combined_rows": len(combined)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
